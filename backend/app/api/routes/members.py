"""회원 — 회원가입 · 로그인 · 로그아웃 · 내 정보 · 비밀번호 변경 · 탈퇴 · 비밀번호 찾기

- 로그인 · 비밀번호 확인을 5번 틀리면 10분 잠금(429).
- 비밀번호를 바꾸면 다른 기기의 로그인은 끊기고 지금 기기는 유지.
- 탈퇴: 예약 기록(FK)을 지키려고 행은 남기고 개인정보만 지운다.
"""
import re
import time

from fastapi import APIRouter, Query, Response
from sqlalchemy import func, select

from app.api.deps import DB, CurrentMember
from app.core.config import get_settings
from app.core.dates import today_kst
from app.core.exceptions import fail
from app.core.security import create_session_token, hash_password, verify_password
from app.models import Member, Reservation
from app.models.reservation import LIVE_STATUSES
from app.schemas.common import Message
from app.schemas.member import (
    IdCheckOut,
    LoginRequest,
    MemberOut,
    PasswordChange,
    PasswordResetRequest,
    ProfileUpdate,
    SignupRequest,
    WithdrawRequest,
)

router = APIRouter(prefix="/members", tags=["members"])

MAX_FAILS = 5
LOCK_SECONDS = 10 * 60
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9-]{9,20}$")

# ---------- 틀린 횟수 잠금 ----------
# ponytail: 서버 메모리에 기록. 서버를 다시 켜거나 여러 대로 늘리면 초기화된다. 필요하면 DB/Redis로.
_fails: dict[str, list[float]] = {}


def check_not_locked(key: str) -> None:
    recent = [t for t in _fails.get(key, []) if t > time.time() - LOCK_SECONDS]
    _fails[key] = recent
    if len(recent) >= MAX_FAILS:
        fail(429, "TOO_MANY_ATTEMPTS", "여러 번 틀려서 10분 동안 잠겼습니다. 잠시 후 다시 시도해 주세요.")


def record_fail(key: str) -> None:
    _fails.setdefault(key, []).append(time.time())


def check_password(member: Member, password: str, key: str, message: str) -> None:
    check_not_locked(key)
    if not verify_password(password, member.password):
        record_fail(key)
        fail(400, "WRONG_PASSWORD", message)


# ---------- 공통 ----------
def set_session(response: Response, member: Member) -> None:
    s = get_settings()
    response.set_cookie(
        s.session_cookie,
        create_session_token(member.member_id, member.password),
        max_age=s.session_seconds,
        httponly=True,
        samesite="lax",
        secure=s.app_env != "local",
    )


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


def ensure_unique(db, login_id: str | None, email: str | None, exclude_id: int | None = None) -> None:
    def taken(column, value):
        # PostgreSQL은 대소문자를 구분해서 비교하므로 소문자로 맞춰 'Guest01'과 'guest01'을 같은 것으로 본다
        q = select(Member.member_id).where(func.lower(column) == value.lower())
        if exclude_id:
            q = q.where(Member.member_id != exclude_id)
        return db.scalar(q) is not None

    if login_id and taken(Member.login_id, login_id):
        fail(409, "DUPLICATE_LOGIN_ID", "이미 사용 중인 아이디입니다.")
    if email and taken(Member.email, email):
        fail(409, "DUPLICATE_EMAIL", "이미 가입된 이메일입니다.")


# ---------- 가입 · 로그인 · 로그아웃 ----------
LOGIN_ID_RE = re.compile(r"^[A-Za-z0-9_]{4,50}$")  # SignupRequest.login_id 와 같은 규칙


@router.get("/check-id", response_model=IdCheckOut)
def check_id(db: DB, login_id: str = Query(alias="loginId")):
    """가입 전 아이디 중복확인. 대소문자는 같은 것으로 본다(가입 때 ensure_unique 와 같은 기준)."""
    login_id = login_id.strip()
    if not LOGIN_ID_RE.match(login_id):
        fail(400, "INVALID_LOGIN_ID", "아이디는 영문 · 숫자 · _ 4~50자입니다.")
    taken = db.scalar(select(Member.member_id).where(func.lower(Member.login_id) == login_id.lower())) is not None
    if taken:
        return IdCheckOut(available=False, message="이미 사용 중인 아이디입니다.")
    return IdCheckOut(available=True, message="사용할 수 있는 아이디입니다.")


@router.post("/signup", response_model=MemberOut, status_code=201)
def signup(body: SignupRequest, db: DB):
    name, phone, email = clean_profile(body.name, body.phone, body.email)
    ensure_unique(db, body.login_id, email)
    member = Member(
        login_id=body.login_id,
        password=hash_password(body.password),
        name=name,
        phone=phone,
        email=email,
        role="USER",  # 가입은 항상 USER. 관리자는 python -m app.db.create_admin
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.post("/login", response_model=MemberOut)
def login(body: LoginRequest, response: Response, db: DB):
    key = f"login:{body.login_id.lower()}"
    check_not_locked(key)
    member = db.scalar(select(Member).where(Member.login_id == body.login_id))
    if member is None or not verify_password(body.password, member.password):
        record_fail(key)
        fail(401, "LOGIN_FAILED", "아이디 또는 비밀번호가 올바르지 않습니다.")
    _fails.pop(key, None)
    set_session(response, member)
    return member


@router.post("/logout", response_model=Message)
def logout(response: Response):
    response.delete_cookie(get_settings().session_cookie)
    return Message(message="로그아웃되었습니다.")


# ---------- 내 정보 ----------
@router.get("/me", response_model=MemberOut)
def me(member: CurrentMember):
    return member


@router.put("/me", response_model=MemberOut)
def update_me(body: ProfileUpdate, member: CurrentMember, db: DB):
    name, phone, email = clean_profile(body.name, body.phone, body.email)
    ensure_unique(db, None, email, exclude_id=member.member_id)
    member.name, member.phone, member.email = name, phone, email
    db.commit()
    return member


@router.put("/me/password", status_code=204)
def change_password(body: PasswordChange, response: Response, member: CurrentMember, db: DB):
    check_password(member, body.current_password, f"password:{member.member_id}", "현재 비밀번호가 맞지 않습니다.")
    member.password = hash_password(body.new_password)
    db.commit()
    set_session(response, member)  # 다른 기기는 끊기고, 지금 화면은 새 쿠키로 로그인 유지


@router.post("/me/withdraw", status_code=204)
def withdraw(body: WithdrawRequest, response: Response, member: CurrentMember, db: DB):
    if member.role == "ADMIN":
        fail(400, "ADMIN_CANNOT_WITHDRAW", "관리자 계정은 탈퇴할 수 없습니다.")
    check_password(member, body.password, f"password:{member.member_id}", "비밀번호가 맞지 않습니다.")
    live = db.scalar(
        select(func.count()).where(
            Reservation.member_id == member.member_id,
            Reservation.status.in_(LIVE_STATUSES),
            Reservation.check_out_date > today_kst(),
        )
    )
    if live:
        fail(409, "HAS_RESERVATION", "진행 중인 예약이 있습니다. 예약을 취소한 뒤 탈퇴해 주세요.")
    member.login_id = f"withdrawn_{member.member_id}"
    member.password = "!"  # 어떤 비밀번호로도 로그인 불가
    member.name, member.phone, member.email = "탈퇴회원", None, None
    db.commit()
    response.delete_cookie(get_settings().session_cookie)


# ---------- 비밀번호 찾기 ----------
@router.post("/password-reset", status_code=204)
def reset_password(body: PasswordResetRequest, db: DB):
    # ponytail: 메일 서버가 없어서 "아이디 + 가입 이메일"이 맞으면 바로 바꾼다.
    # 이메일을 아는 남도 바꿀 수 있으니, 공개 배포 전에 메일로 보내는 일회용 링크로 바꾼다.
    key = f"reset:{body.login_id.lower()}"
    check_not_locked(key)
    member = db.scalar(select(Member).where(Member.login_id == body.login_id))
    if member is None or not member.email or member.email.lower() != body.email.strip().lower():
        record_fail(key)
        fail(400, "NOT_MATCHED", "아이디와 가입한 이메일이 맞지 않습니다.")
    member.password = hash_password(body.new_password)
    db.commit()
