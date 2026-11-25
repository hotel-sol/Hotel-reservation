"""회원 — 회원가입 · 로그인 · 로그아웃 · 내 정보 · 비밀번호 변경 · 탈퇴 · 비밀번호 찾기

- 로그인 · 비밀번호 확인을 10분 안에 5번 틀리면 10분 잠금(429). 기록은 login_attempt 테이블.
  로그인에 성공한 적 있는 기기는 따로 세서, 남이 일부러 잠가도 주인은 들어올 수 있다.
- 비밀번호 찾기는 시연 전까지 꺼 둔다(#67-1).
- 비밀번호를 바꾸면 다른 기기의 로그인은 끊기고 지금 기기는 유지.
- 탈퇴: 예약 기록(FK)을 지키려고 행은 남기고 개인정보만 지운다.
"""
import re
from typing import Annotated

from fastapi import APIRouter, Cookie, Query, Response
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import DB, CurrentMember
from app.core.config import get_settings
from app.core.dates import today_kst
from app.core.exceptions import fail
from app.core.security import (
    DEVICE_SECONDS,
    create_device_token,
    create_session_token,
    hash_password,
    read_device_token,
    verify_password,
)
from app.models import Member, Reservation
from app.models.reservation import LIVE_STATUSES
from app.schemas.common import Message
from app.schemas.member import (
    IdCheckOut,
    LoginRequest,
    MemberOut,
    PasswordChange,
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
# 실패 기록은 login_attempt 테이블에 남긴다(1-A3). 서버를 다시 켜거나 여러 대로 늘려도 잠금이 유지된다.
# 시간은 DB 시계(LOCALTIMESTAMP) 하나로만 비교해서 서버 · DB 시간대가 달라도 맞는다.
_RECENT = "attempt_key = :k AND failed_at >= LOCALTIMESTAMP - make_interval(secs => :s)"


def check_not_locked(db: Session, key: str) -> None:
    """같은 key 로 동시에 여러 번 보내도 5번을 넘지 않게, 이 key 의 시도를 한 줄로 세운다.
    (DB 잠금 pg_advisory_xact_lock: 이 요청이 commit/rollback 할 때까지 같은 key 의 다음 요청은 기다린다.
    그래서 호출한 쪽은 비밀번호 확인 뒤 record_fail · clear_fails · commit 중 하나로 끝내야 한다.)"""
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": key})
    db.execute(text("DELETE FROM login_attempt WHERE attempt_key = :k "
                    "AND failed_at < LOCALTIMESTAMP - make_interval(secs => :s)"), {"k": key, "s": LOCK_SECONDS})
    recent = db.scalar(text(f"SELECT COUNT(*) FROM login_attempt WHERE {_RECENT}"), {"k": key, "s": LOCK_SECONDS})
    if recent >= MAX_FAILS:
        db.rollback()
        fail(429, "TOO_MANY_ATTEMPTS", "여러 번 틀려서 10분 동안 잠겼습니다. 잠시 후 다시 시도해 주세요.")


def record_fail(db: Session, key: str) -> None:
    # 바로 commit: 뒤이어 fail() 로 요청이 끝나도 기록은 남아야 한다
    db.execute(text("INSERT INTO login_attempt (attempt_key) VALUES (:k)"), {"k": key})
    db.commit()


def clear_fails(db: Session, key: str) -> None:
    db.execute(text("DELETE FROM login_attempt WHERE attempt_key = :k"), {"k": key})
    db.commit()


def check_password(db: Session, member: Member, password: str, key: str, message: str) -> None:
    check_not_locked(db, key)
    if not verify_password(password, member.password):
        record_fail(db, key)
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


def clean_profile(name: str, phone: str | None, email: str | None) -> tuple[str, str, str | None]:
    """가입 · 정보 수정 공통 검사. 앞뒤 공백을 지우고 빈 값은 NULL로."""
    name = name.strip()
    phone = (phone or "").strip() or None
    email = (email or "").strip() or None
    if not name:
        fail(400, "INVALID_INPUT", "이름을 입력해 주세요.")
    if not phone:
        fail(400, "INVALID_PHONE", "전화번호를 입력해 주세요.")
    if not PHONE_RE.match(phone):
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


def commit_unique(db, login_id: str | None, email: str | None, exclude_id: int | None = None) -> None:
    """두 사람이 거의 동시에 같은 아이디 · 이메일로 저장하면 ensure_unique 를 둘 다 통과하고
    DB의 lower() UNIQUE 인덱스가 늦은 쪽을 막는다. 그때도 500 대신 같은 409 문구로 답한다."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        ensure_unique(db, login_id, email, exclude_id)
        raise


# ---------- 가입 · 로그인 · 로그아웃 ----------
LOGIN_ID_RE = re.compile(r"^[A-Za-z0-9_]{4,20}$")  # SignupRequest.login_id 와 같은 규칙


@router.get("/check-id", response_model=IdCheckOut)
def check_id(db: DB, login_id: str = Query(alias="loginId")):
    """가입 전 아이디 중복확인. 대소문자는 같은 것으로 본다(가입 때 ensure_unique 와 같은 기준)."""
    login_id = login_id.strip()
    if not LOGIN_ID_RE.match(login_id):
        fail(400, "INVALID_LOGIN_ID", "아이디는 영문 · 숫자 · _ 4~20자입니다.")
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
    commit_unique(db, body.login_id, email)
    db.refresh(member)
    return member


DEVICE_COOKIE = "hotel_device"
_DUMMY_HASH = hash_password("timing-equalizer")  # 어떤 비밀번호와도 맞지 않는 값(서버 켤 때 한 번 만듦)


@router.post("/login", response_model=MemberOut)
def login(
    body: LoginRequest,
    response: Response,
    db: DB,
    device: Annotated[str | None, Cookie(alias=DEVICE_COOKIE)] = None,
):
    # 잠금(10분 안 5번)은 두 가지로 센다(#67-3):
    #  - 이 아이디로 로그인에 성공한 적 있는 기기(서명된 hotel_device 쿠키) → 그 기기만 따로 센다
    #  - 처음 보는 기기 → 아이디 하나로 함께 센다
    # 그래서 남이 내 아이디로 일부러 5번 틀려도, 전에 쓰던 내 기기에서는 들어올 수 있다.
    # 비밀번호 맞혀 보기는 그대로 막힌다(기기 표는 로그인에 성공해야만 받을 수 있음).
    # (아이디, IP)로 나누지 않은 까닭: Next /api 프록시가 손님이 보낸 X-Forwarded-For 를 그대로 넘겨서 꾸밀 수 있다.
    member = db.scalar(select(Member).where(Member.login_id == body.login_id))
    known = read_device_token(device) if device else None
    trusted = member is not None and known is not None and known[0] == member.member_id
    key = f"device:{member.member_id}:{known[1]}" if trusted else f"login:{body.login_id.lower()}"
    check_not_locked(db, key)
    # 없는 아이디도 같은 시간이 걸리게 가짜 해시로 한 번 확인한다(응답 속도로 아이디가 있는지 알아내기 막기)
    if not verify_password(body.password, member.password if member else _DUMMY_HASH) or member is None:
        record_fail(db, key)
        fail(401, "LOGIN_FAILED", "아이디 또는 비밀번호가 올바르지 않습니다.")
    clear_fails(db, key)
    set_session(response, member)
    if not trusted:
        s = get_settings()
        response.set_cookie(DEVICE_COOKIE, create_device_token(member.member_id), max_age=DEVICE_SECONDS,
                            httponly=True, samesite="lax", secure=s.app_env != "local")
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
    commit_unique(db, None, email, exclude_id=member.member_id)
    return member


@router.put("/me/password", status_code=204)
def change_password(body: PasswordChange, response: Response, member: CurrentMember, db: DB):
    check_password(db, member, body.current_password, f"password:{member.member_id}", "현재 비밀번호가 맞지 않습니다.")
    member.password = hash_password(body.new_password)
    db.commit()
    set_session(response, member)  # 다른 기기는 끊기고, 지금 화면은 새 쿠키로 로그인 유지


@router.post("/me/withdraw", status_code=204)
def withdraw(body: WithdrawRequest, response: Response, member: CurrentMember, db: DB):
    if member.role == "ADMIN":
        fail(400, "ADMIN_CANNOT_WITHDRAW", "관리자 계정은 탈퇴할 수 없습니다.")
    check_password(db, member, body.password, f"password:{member.member_id}", "비밀번호가 맞지 않습니다.")
    live = db.scalar(
        select(func.count()).where(
            Reservation.member_id == member.member_id,
            Reservation.status.in_(LIVE_STATUSES),
            Reservation.check_out_date > today_kst(),
        )
    )
    if live:
        fail(409, "HAS_RESERVATION", "진행 중인 예약이 있습니다. 예약을 취소한 뒤 탈퇴해 주세요.")
    # "-" 는 가입 아이디에 못 쓰는 기호라 누가 먼저 가입해 둘 수 없다(#67-4: withdrawn_N 선점 → 탈퇴 500)
    member.login_id = f"withdrawn-{member.member_id}"
    member.password = "!"  # 어떤 비밀번호로도 로그인 불가
    member.name, member.phone, member.email = "탈퇴회원", None, None
    db.commit()
    response.delete_cookie(get_settings().session_cookie)


# ---------- 비밀번호 찾기 ----------
@router.post("/password-reset", status_code=204)
def reset_password():
    # 시연 전에는 끈다(#67-1): 메일 서버가 없어서 "아이디 + 가입 이메일"만 맞으면 바로 바꾸는 방식이었는데,
    # 이메일만 알아내면 남의 계정(관리자 포함)을 빼앗을 수 있었다. 정식은 메일 일회용 링크(1-A4).
    fail(403, "PASSWORD_RESET_DISABLED", "비밀번호 찾기는 지금 쓸 수 없습니다. 호텔 프런트에 문의해 주세요.")
