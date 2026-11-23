"""공통 의존성: DB 세션, 로그인 회원, 관리자 확인.

사용 예)
    def handler(member: Member = Depends(current_member)): ...
    @router.get(..., dependencies=[Depends(require_admin)])
"""
from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import fail
from app.core.security import read_session_token
from app.db.session import get_db
from app.models import Member

DB = Annotated[Session, Depends(get_db)]


def current_member(
    db: DB,
    hotel_session: Annotated[str | None, Cookie(alias=get_settings().session_cookie)] = None,
) -> Member:
    member_id = read_session_token(hotel_session) if hotel_session else None
    member = db.get(Member, member_id) if member_id else None
    if member is None:
        fail(401, "UNAUTHORIZED", "로그인이 필요합니다.")
    return member


def require_admin(member: Annotated[Member, Depends(current_member)]) -> Member:
    if member.role != "ADMIN":
        fail(403, "FORBIDDEN", "관리자만 접근할 수 있습니다.")
    return member


CurrentMember = Annotated[Member, Depends(current_member)]
AdminMember = Annotated[Member, Depends(require_admin)]
