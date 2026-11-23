"""회원 — 자체 회원가입 · 로그인 · 로그아웃 (테이블 member)

POST /members/signup   회원가입 (항상 USER로 가입)
POST /members/login    로그인 → 세션 쿠키 발급
POST /members/logout   로그아웃 → 쿠키 삭제
GET  /members/me       지금 로그인한 사람 {memberId, loginId, name, role}, 아니면 401
GET  /signup, /login   가입 · 로그인 화면
GET  /logout           로그아웃 후 로그인 화면으로 (상단 메뉴 링크용)

다른 파트에서 로그인 확인: Depends(current_member), 관리자만: Depends(require_admin)
다른 앱에 붙일 때: app.include_router(member.router)
혼자 실행: uvicorn member:app --reload  (backend/member 폴더에서)
"""
import hashlib
import hmac
import os
import re
import secrets
import time
from pathlib import Path

import pymysql
from fastapi import APIRouter, Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

HERE = Path(__file__).parent
SESSION_COOKIE = "hotel_session"
SESSION_SECONDS = 60 * 60 * 8  # 8시간
# ponytail: 비밀키가 환경변수에 없으면 실행할 때마다 새로 만든다 → 서버를 다시 켜면 모두 로그아웃. 배포 땐 SESSION_SECRET 설정.
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_hex(32)
DUPLICATE_KEY = 1062

LOGIN_ID_RE = re.compile(r"^[A-Za-z0-9_]{4,50}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9-]{9,20}$")


def connect():
    # ponytail: 공통 backend/db/connect.py가 채워지면 그쪽으로 바꾼다.
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "hotel"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def fail(status: int, code: str, message: str):
    raise HTTPException(status, detail={"code": code, "message": message})


# ---------- 비밀번호: 표준 라이브러리 scrypt, "scrypt$소금$해시"로 저장 ----------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)


# ---------- 세션: "회원번호.만료시각.서명" 쿠키 (서명이 맞아야 믿는다) ----------
def _sign(payload: str) -> str:
    return hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_session(member_id: int) -> str:
    payload = f"{member_id}.{int(time.time()) + SESSION_SECONDS}"
    return f"{payload}.{_sign(payload)}"


def read_session(token: str | None) -> int | None:
    if not token:
        return None
    try:
        member_id, expires, sig = token.split(".")
        if not hmac.compare_digest(sig, _sign(f"{member_id}.{expires}")):
            return None
        if int(expires) < time.time():
            return None
        return int(member_id)
    except ValueError:
        return None


def current_member(hotel_session: str | None = Cookie(default=None), db=Depends(get_db)) -> dict:
    """로그인한 회원. 역할(role)은 매번 DB에서 읽어서 바뀌면 바로 반영된다."""
    member_id = read_session(hotel_session)
    if member_id is None:
        fail(401, "UNAUTHORIZED", "로그인이 필요합니다.")
    with db.cursor() as cur:
        cur.execute("SELECT member_id, login_id, name, role FROM member WHERE member_id = %s", (member_id,))
        member = cur.fetchone()
    if member is None:
        fail(401, "UNAUTHORIZED", "로그인이 필요합니다.")
    return member


def require_admin(member: dict = Depends(current_member)) -> dict:
    if member["role"] != "ADMIN":
        fail(403, "FORBIDDEN", "관리자만 사용할 수 있습니다.")
    return member


def to_json(m: dict) -> dict:
    return {"memberId": m["member_id"], "loginId": m["login_id"], "name": m["name"], "role": m["role"]}


# ---------- API ----------
class SignupIn(BaseModel):
    login_id: str = Field(alias="loginId")
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)


class LoginIn(BaseModel):
    login_id: str = Field(alias="loginId")
    password: str


router = APIRouter(tags=["회원"])


@router.post("/members/signup", status_code=201)
def signup(body: SignupIn, db=Depends(get_db)):
    name = body.name.strip()
    phone = (body.phone or "").strip() or None
    email = (body.email or "").strip() or None
    if not LOGIN_ID_RE.match(body.login_id):
        fail(400, "INVALID_LOGIN_ID", "아이디는 영문 · 숫자 · _ 4~50자입니다.")
    if not name:
        fail(400, "INVALID_INPUT", "이름을 입력해 주세요.")
    if phone and not PHONE_RE.match(phone):
        fail(400, "INVALID_PHONE", "전화번호는 숫자와 - 만 씁니다.")
    if email and not EMAIL_RE.match(email):
        fail(400, "INVALID_EMAIL", "이메일 형식이 아닙니다.")

    try:
        with db.cursor() as cur:
            # role은 받지 않는다. 가입은 항상 USER, 관리자는 DB에서 따로 지정(readme).
            cur.execute(
                "INSERT INTO member (login_id, password, name, phone, email) VALUES (%s, %s, %s, %s, %s)",
                (body.login_id, hash_password(body.password), name, phone, email),
            )
            cur.execute("SELECT member_id, login_id, name, role FROM member WHERE member_id = %s", (cur.lastrowid,))
            member = cur.fetchone()
        db.commit()
    except pymysql.IntegrityError as e:
        db.rollback()
        if e.args[0] == DUPLICATE_KEY:
            if "email" in str(e.args[1]):
                fail(409, "DUPLICATE_EMAIL", "이미 가입된 이메일입니다.")
            fail(409, "DUPLICATE_LOGIN_ID", "이미 사용 중인 아이디입니다.")
        raise
    return to_json(member)


@router.post("/members/login")
def login(body: LoginIn, response: Response, db=Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT member_id, login_id, name, role, password FROM member WHERE login_id = %s",
                    (body.login_id,))
        member = cur.fetchone()
    # ponytail: 로그인 시도 횟수 제한 없음. 공개 배포 전에 추가.
    if member is None or not verify_password(body.password, member["password"]):
        fail(401, "LOGIN_FAILED", "아이디 또는 비밀번호가 맞지 않습니다.")
    response.set_cookie(SESSION_COOKIE, make_session(member["member_id"]), max_age=SESSION_SECONDS,
                        httponly=True, samesite="lax")
    return to_json(member)


@router.post("/members/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)


@router.get("/members/me")
def me(member: dict = Depends(current_member)):
    return to_json(member)


@router.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(HERE / "login.html")


@router.get("/signup", include_in_schema=False)
def signup_page():
    return FileResponse(HERE / "signup.html")


@router.get("/logout", include_in_schema=False)
def logout_page():
    # ponytail: 상단 메뉴의 링크로 로그아웃(GET). 남이 링크로 로그아웃시킬 수는 있지만 그 이상 피해는 없다.
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


app = FastAPI(title="태양의 호텔 · 회원")
app.include_router(router)

# 혼자 실행할 때 상단 메뉴(frontend/layout)가 있으면 같이 연다. 메인 앱에서는 메인 앱이 연다.
_layout = HERE.parent.parent / "frontend" / "layout"
if _layout.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/layout", StaticFiles(directory=_layout), name="layout")
