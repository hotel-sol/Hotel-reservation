"""상단 메뉴 (공통) — 로그인 역할에 맞는 메뉴 트리"""
from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DB, SessionCookie, member_from_cookie
from app.models import Menu
from app.schemas.menu import MenuOut

router = APIRouter(prefix="/menus", tags=["menus"])


@router.get("", response_model=list[MenuOut])
def list_menus(db: DB, hotel_session: SessionCookie = None):
    member = member_from_cookie(db, hotel_session)
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
