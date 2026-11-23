"""회원 — 회원가입 · 로그인 · 로그아웃 · 내 정보"""
from fastapi import APIRouter, Response
from sqlalchemy import or_, select

from app.api.deps import DB, CurrentMember
from app.core.config import get_settings
from app.core.exceptions import fail
from app.core.security import create_session_token, hash_password, verify_password
from app.models import Member
from app.schemas.common import Message
from app.schemas.member import LoginRequest, MemberOut, SignupRequest

router = APIRouter(prefix="/members", tags=["members"])


@router.post("/signup", response_model=MemberOut, status_code=201)
def signup(body: SignupRequest, db: DB):
    dup = db.scalar(
        select(Member).where(
            or_(Member.login_id == body.login_id, (Member.email == body.email) if body.email else False)
        )
    )
    if dup:
        fail(409, "DUPLICATE_MEMBER", "이미 사용 중인 아이디 또는 이메일입니다.")
    member = Member(
        login_id=body.login_id,
        password=hash_password(body.password),
        name=body.name,
        phone=body.phone,
        email=body.email,
        role="USER",  # 가입은 항상 USER
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.post("/login", response_model=MemberOut)
def login(body: LoginRequest, response: Response, db: DB):
    # TODO: 로그인 5회 실패 시 10분 잠금 (참고 저장소 member.py)
    member = db.scalar(select(Member).where(Member.login_id == body.login_id))
    if member is None or not verify_password(body.password, member.password):
        fail(401, "LOGIN_FAILED", "아이디 또는 비밀번호가 올바르지 않습니다.")
    s = get_settings()
    response.set_cookie(
        s.session_cookie,
        create_session_token(member.member_id),
        max_age=s.session_seconds,
        httponly=True,
        samesite="lax",
        secure=s.app_env != "local",
    )
    return member


@router.post("/logout", response_model=Message)
def logout(response: Response):
    response.delete_cookie(get_settings().session_cookie)
    return Message(message="로그아웃되었습니다.")


@router.get("/me", response_model=MemberOut)
def me(member: CurrentMember):
    return member


# TODO: PUT /members/me, PUT /members/me/password, POST /members/me/withdraw, POST /members/password-reset
