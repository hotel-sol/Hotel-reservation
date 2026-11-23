"""상단 메뉴 (공통) — 로그인 역할에 맞는 메뉴 트리"""
from fastapi import APIRouter, Cookie
from sqlalchemy import select

from app.api.deps import DB
from app.core.security import read_session_token
from app.models import Member, Menu
from app.schemas.menu import MenuOut

router = APIRouter(prefix="/menus", tags=["menus"])


@router.get("", response_model=list[MenuOut])
def list_menus(db: DB, hotel_session: str | None = Cookie(default=None)):
    member_id = read_session_token(hotel_session) if hotel_session else None
    member = db.get(Member, member_id) if member_id else None
    roles = ["USER", "ADMIN"] if member and member.role == "ADMIN" else ["USER"]

    rows = db.scalars(
        select(Menu).where(Menu.is_used == "Y", Menu.role.in_(roles)).order_by(Menu.sort_order, Menu.menu_id)
    ).all()
    nodes = {m.menu_id: MenuOut.model_validate(m) for m in rows}
    tree: list[MenuOut] = []
    for node in nodes.values():
        parent = nodes.get(node.parent_id) if node.parent_id else None
        (parent.children if parent else tree).append(node)
    return tree
