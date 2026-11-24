"""상단 메뉴 (공통) — 로그인 역할에 맞는 메뉴 트리

- 관리자(ADMIN): 관리자 메뉴만 (객실 관리 · 예약 일자 관리 · 예약 관리). 설계서 ADM 화면 상단과 같음
- 손님(USER) · 로그인 안 함: 손님 메뉴만 (객실 추천 · 내 예약)
"""
from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DB, SessionCookie, member_from_cookie
from app.models import Menu
from app.schemas.menu import MenuOut

router = APIRouter(prefix="/menus", tags=["menus"])


@router.get("", response_model=list[MenuOut])
def list_menus(db: DB, hotel_session: SessionCookie = None):
    member = member_from_cookie(db, hotel_session)
    # 손님 메뉴와 관리자 메뉴를 섞으면 sort_order(둘 다 1부터)끼리 엇갈려 나오므로 역할 하나만 보여준다
    role = "ADMIN" if member and member.role == "ADMIN" else "USER"

    rows = db.scalars(
        select(Menu).where(Menu.is_used == "Y", Menu.role == role).order_by(Menu.sort_order, Menu.menu_id)
    ).all()
    nodes = {m.menu_id: MenuOut.model_validate(m) for m in rows}
    tree: list[MenuOut] = []
    for node in nodes.values():
        parent = nodes.get(node.parent_id) if node.parent_id else None
        (parent.children if parent else tree).append(node)
    return tree
