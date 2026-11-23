"""공통 의존성: DB 세션, 로그인 회원, 관리자 확인.

사용 예)
    def handler(member: CurrentMember): ...
    @router.get(..., dependencies=[Depends(require_admin)])
"""
import hmac
from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import fail
from app.core.security import password_tag, read_session_token
from app.db.session import get_db
from app.models import Member

DB = Annotated[Session, Depends(get_db)]
SessionCookie = Annotated[str | None, Cookie(alias=get_settings().session_cookie)]


def member_from_cookie(db: Session, token: str | None) -> Member | None:
    """쿠키가 맞고 그 뒤로 비밀번호가 안 바뀌었으면 회원, 아니면 None. 역할은 매번 DB에서 읽는다."""
    session = read_session_token(token) if token else None
    if session is None:
        return None
    member_id, tag = session
    member = db.get(Member, member_id)
    if member is None or not hmac.compare_digest(tag, password_tag(member.password)):
        return None
    return member


def current_member(db: DB, hotel_session: SessionCookie = None) -> Member:
    member = member_from_cookie(db, hotel_session)
    if member is None:
        fail(401, "UNAUTHORIZED", "로그인이 필요합니다.")
    return member


def require_admin(member: Annotated[Member, Depends(current_member)]) -> Member:
    if member.role != "ADMIN":
        fail(403, "FORBIDDEN", "관리자만 접근할 수 있습니다.")
    return member


CurrentMember = Annotated[Member, Depends(current_member)]
AdminMember = Annotated[Member, Depends(require_admin)]
