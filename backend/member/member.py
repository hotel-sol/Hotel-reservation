"""회원 — 자체 회원가입 · 로그인 · 로그아웃 · 내 정보 (테이블 member)

API(router, 실제 주소는 앞에 /api):
POST /members/signup            회원가입 (항상 USER로 가입)
POST /members/login             로그인 → 세션 쿠키 발급 (5번 틀리면 10분 잠금)
POST /members/logout            로그아웃 → 쿠키 삭제
GET  /members/me                지금 로그인한 사람 {memberId, loginId, name, phone, email, role}, 아니면 401
PUT  /members/me                내 정보 수정 (이름 · 전화번호 · 이메일)
PUT  /members/me/password       비밀번호 변경 (현재 비밀번호 확인)
POST /members/me/withdraw       탈퇴 (비밀번호 확인, 개인정보 삭제)
POST /members/password-reset    비밀번호 찾기 (아이디 + 가입 이메일 확인 후 새 비밀번호)

임시 HTML 화면(pages, /api 없음):
GET  /signup /login /mypage /password-reset   화면
GET  /logout                    로그아웃 후 로그인 화면으로 (상단 메뉴 링크용)

다른 파트에서 로그인 확인: from member.member import current_member, require_admin
    Depends(current_member)  로그인한 회원,  Depends(require_admin)  관리자만
관리자 계정 만들기: python -m member.create_admin <아이디> <이름>
"""
import hashlib
import hmac
import logging
import os
import re
import secrets
import time
from pathlib import Path

import pymysql
from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from common.common import DUPLICATE_KEY, LIVE_STATUSES, fail
from db.connect import get_db

HERE = Path(__file__).parent
SESSION_COOKIE = "hotel_session"
SESSION_SECONDS = 60 * 60 * 8  # 8시간
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_hex(32)
if not os.getenv("SESSION_SECRET"):
    logging.getLogger("member").warning(
        "SESSION_SECRET 환경변수가 없어 임시 비밀키를 씁니다. 서버를 다시 켜면 모두 로그아웃됩니다.")

MAX_FAILS = 5
LOCK_SECONDS = 10 * 60

LOGIN_ID_RE = re.compile(r"^[A-Za-z0-9_]{4,50}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9-]{9,20}$")
MEMBER_COLUMNS = "member_id, login_id, name, phone, email, role, password"


# ---------- 비밀번호: 회원별 무작위 salt + scrypt 해시, "scrypt$salt$hash"로 저장 ----------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False                      # 탈퇴 회원("!")처럼 형식이 다르면 항상 실패
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)


# ---------- 로그인 실패 잠금 ----------
# ponytail: 서버 메모리에 저장. 서버가 여러 대이거나 재시작하면 초기화된다. 필요하면 DB/Redis로.
_fails: dict[str, list[float]] = {}


def check_not_locked(key: str) -> None:
    recent = [t for t in _fails.get(key, []) if t > time.time() - LOCK_SECONDS]
    _fails[key] = recent
    if len(recent) >= MAX_FAILS:
        fail(429, "TOO_MANY_ATTEMPTS", "여러 번 틀려서 10분 동안 잠겼습니다. 잠시 후 다시 시도해 주세요.")


def record_fail(key: str) -> None:
    _fails.setdefault(key, []).append(time.time())


# ---------- 세션 쿠키: "회원번호.만료시각.비밀번호표식.서명" ----------
# 비밀번호표식 = 저장된 비밀번호 해시의 앞부분. 비밀번호를 바꾸거나 탈퇴하면 예전 쿠키가 모두 무효가 된다.
def _sign(payload: str) -> str:
    return hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _pw_tag(stored_password: str) -> str:
    return hashlib.sha256(stored_password.encode()).hexdigest()[:12]


def make_session(member_id: int, stored_password: str) -> str:
    payload = f"{member_id}.{int(time.time()) + SESSION_SECONDS}.{_pw_tag(stored_password)}"
    return f"{payload}.{_sign(payload)}"


def read_session(token: str | None) -> tuple[int, str] | None:
    """서명과 만료가 맞으면 (회원번호, 비밀번호표식)."""
    if not token:
        return None
    try:
        member_id, expires, tag, sig = token.split(".")
        if not hmac.compare_digest(sig, _sign(f"{member_id}.{expires}.{tag}")):
            return None
        if int(expires) < time.time():
            return None
        return int(member_id), tag
    except ValueError:
        return None


def set_session(response: Response, member: dict) -> None:
    response.set_cookie(SESSION_COOKIE, make_session(member["member_id"], member["password"]),
                        max_age=SESSION_SECONDS, httponly=True, samesite="lax")


def find_member(cur, where: str, value) -> dict | None:
    cur.execute(f"SELECT {MEMBER_COLUMNS} FROM member WHERE {where} = %s", (value,))
    return cur.fetchone()


def current_member(hotel_session: str | None = Cookie(default=None), db=Depends(get_db)) -> dict:
    """로그인한 회원. 역할(role)은 매번 DB에서 읽어서 바뀌면 바로 반영된다."""
    session = read_session(hotel_session)
    if session is None:
        fail(401, "UNAUTHORIZED", "로그인이 필요합니다.")
    member_id, tag = session
    with db.cursor() as cur:
        member = find_member(cur, "member_id", member_id)
    if member is None or not hmac.compare_digest(tag, _pw_tag(member["password"])):
        fail(401, "UNAUTHORIZED", "로그인이 필요합니다.")
    return member


def require_admin(member: dict = Depends(current_member)) -> dict:
    if member["role"] != "ADMIN":
        fail(403, "FORBIDDEN", "관리자만 사용할 수 있습니다.")
    return member


def to_json(m: dict) -> dict:
    return {"memberId": m["member_id"], "loginId": m["login_id"], "name": m["name"],
            "phone": m["phone"], "email": m["email"], "role": m["role"]}


def clean_profile(name: str, phone: str | None, email: str | None) -> tuple[str, str | None, str | None]:
    """가입 · 정보 수정 공통 검사. 앞뒤 공백을 지우고 빈 값은 NULL로."""
    name = name.strip()
    phone = (phone or "").strip() or None
    email = (email or "").strip() or None
    if not name:
        fail(400, "INVALID_INPUT", "이름을 입력해 주세요.")
    if phone and not PHONE_RE.match(phone):
        fail(400, "INVALID_PHONE", "전화번호는 숫자와 - 만 씁니다.")
    if email and not EMAIL_RE.match(email):
        fail(400, "INVALID_EMAIL", "이메일 형식이 아닙니다.")
    return name, phone, email


def duplicate_error(e: pymysql.IntegrityError):
    if e.args[0] != DUPLICATE_KEY:
        raise e
    if "email" in str(e.args[1]):
        fail(409, "DUPLICATE_EMAIL", "이미 가입된 이메일입니다.")
    fail(409, "DUPLICATE_LOGIN_ID", "이미 사용 중인 아이디입니다.")


# ---------- 요청 모양 ----------
class SignupIn(BaseModel):
    login_id: str = Field(alias="loginId")
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)


class LoginIn(BaseModel):
    login_id: str = Field(alias="loginId")
    password: str


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(alias="currentPassword")
    new_password: str = Field(alias="newPassword", min_length=8, max_length=100)


class WithdrawIn(BaseModel):
    password: str


class PasswordResetIn(BaseModel):
    login_id: str = Field(alias="loginId")
    email: str
    new_password: str = Field(alias="newPassword", min_length=8, max_length=100)


router = APIRouter(tags=["회원"])


# ---------- 가입 · 로그인 · 로그아웃 ----------
@router.post("/members/signup", status_code=201)
def signup(body: SignupIn, db=Depends(get_db)):
    if not LOGIN_ID_RE.match(body.login_id):
        fail(400, "INVALID_LOGIN_ID", "아이디는 영문 · 숫자 · _ 4~50자입니다.")
    name, phone, email = clean_profile(body.name, body.phone, body.email)
    try:
        with db.cursor() as cur:
            # role은 받지 않는다. 가입은 항상 USER, 관리자는 create_admin.py로 만든다.
            cur.execute(
                "INSERT INTO member (login_id, password, name, phone, email) VALUES (%s, %s, %s, %s, %s)",
                (body.login_id, hash_password(body.password), name, phone, email),
            )
            member = find_member(cur, "member_id", cur.lastrowid)
        db.commit()
    except pymysql.IntegrityError as e:
        db.rollback()
        duplicate_error(e)
    return to_json(member)


@router.post("/members/login")
def login(body: LoginIn, response: Response, db=Depends(get_db)):
    key = f"login:{body.login_id.lower()}"
    check_not_locked(key)
    with db.cursor() as cur:
        member = find_member(cur, "login_id", body.login_id)
    if member is None or not verify_password(body.password, member["password"]):
        record_fail(key)
        fail(401, "LOGIN_FAILED", "아이디 또는 비밀번호가 맞지 않습니다.")
    _fails.pop(key, None)
    set_session(response, member)
    return to_json(member)


@router.post("/members/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)


# ---------- 내 정보 ----------
@router.get("/members/me")
def me(member: dict = Depends(current_member)):
    return to_json(member)


@router.put("/members/me")
def update_me(body: ProfileIn, member: dict = Depends(current_member), db=Depends(get_db)):
    name, phone, email = clean_profile(body.name, body.phone, body.email)
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE member SET name = %s, phone = %s, email = %s WHERE member_id = %s",
                        (name, phone, email, member["member_id"]))
            updated = find_member(cur, "member_id", member["member_id"])
        db.commit()
    except pymysql.IntegrityError as e:
        db.rollback()
        duplicate_error(e)
    return to_json(updated)


def save_password(db, member_id: int, new_password: str) -> dict:
    with db.cursor() as cur:
        cur.execute("UPDATE member SET password = %s WHERE member_id = %s", (hash_password(new_password), member_id))
        updated = find_member(cur, "member_id", member_id)
    db.commit()
    return updated


@router.put("/members/me/password", status_code=204)
def change_password(body: PasswordChangeIn, response: Response,
                    member: dict = Depends(current_member), db=Depends(get_db)):
    key = f"password:{member['member_id']}"
    check_not_locked(key)
    if not verify_password(body.current_password, member["password"]):
        record_fail(key)
        fail(400, "WRONG_PASSWORD", "현재 비밀번호가 맞지 않습니다.")
    updated = save_password(db, member["member_id"], body.new_password)
    set_session(response, updated)        # 다른 기기의 로그인은 끊기고, 지금 화면은 그대로 로그인 유지


@router.post("/members/me/withdraw", status_code=204)
def withdraw(body: WithdrawIn, response: Response, member: dict = Depends(current_member), db=Depends(get_db)):
    """예약 기록(FK)은 남겨야 해서 행을 지우지 않고 개인정보만 지운다."""
    if member["role"] == "ADMIN":
        fail(400, "ADMIN_CANNOT_WITHDRAW", "관리자 계정은 탈퇴할 수 없습니다.")
    key = f"password:{member['member_id']}"
    check_not_locked(key)
    if not verify_password(body.password, member["password"]):
        record_fail(key)
        fail(400, "WRONG_PASSWORD", "비밀번호가 맞지 않습니다.")
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM reservation WHERE member_id = %s AND status IN %s"
                    " AND check_out_date > CURDATE()", (member["member_id"], LIVE_STATUSES))
        if cur.fetchone()["n"]:
            fail(409, "HAS_RESERVATION", "진행 중인 예약이 있습니다. 예약을 취소한 뒤 탈퇴해 주세요.")
        mid = member["member_id"]
        cur.execute("UPDATE member SET login_id = %s, password = '!', name = '탈퇴회원', phone = NULL, email = NULL"
                    " WHERE member_id = %s", (f"withdrawn_{mid}", mid))
    db.commit()
    response.delete_cookie(SESSION_COOKIE)


# ---------- 비밀번호 찾기 ----------
@router.post("/members/password-reset", status_code=204)
def reset_password(body: PasswordResetIn, db=Depends(get_db)):
    # ponytail: 메일 서버가 없어서 "아이디 + 가입 이메일"이 맞으면 바로 새 비밀번호로 바꾼다.
    # 이메일을 아는 남도 바꿀 수 있으니, 공개 배포 전에 메일로 보내는 일회용 링크로 바꾼다.
    key = f"reset:{body.login_id.lower()}"
    check_not_locked(key)
    with db.cursor() as cur:
        member = find_member(cur, "login_id", body.login_id)
    email_ok = member is not None and member["email"] and member["email"].lower() == body.email.strip().lower()
    if not email_ok:
        record_fail(key)
        fail(400, "NOT_MATCHED", "아이디와 가입한 이메일이 맞지 않습니다.")
    save_password(db, member["member_id"], body.new_password)


# ---------- 임시 HTML 화면 (Next.js 화면이 생기면 지운다) ----------
pages = APIRouter(include_in_schema=False)


def page(name: str):
    return lambda: FileResponse(HERE / name)


for _path, _file in {"/login": "login.html", "/signup": "signup.html",
                     "/mypage": "mypage.html", "/password-reset": "password-reset.html"}.items():
    pages.add_api_route(_path, page(_file), methods=["GET"])


@pages.get("/logout")
def logout_page():
    # ponytail: 상단 메뉴의 링크로 로그아웃(GET). 남이 링크로 로그아웃시킬 수는 있지만 그 이상 피해는 없다.
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
