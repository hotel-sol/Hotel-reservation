"""상단 메뉴 (공통) — 로그인 역할에 맞는 메뉴 트리

- 손님(USER) · 로그인 안 함: 손님 메뉴만 (객실 추천 · 내 예약)
- 관리자(ADMIN): 손님 메뉴 + 관리자 메뉴를 함께 내려준다(각 항목의 role 로 구분).
  화면(Header)이 지금 영역에 맞는 묶음만 보여준다: /admin/* = 관리자 메뉴, 그 밖 = 손님 메뉴.
  관리자는 오른쪽 위 버튼으로 "관리자 페이지" ↔ "고객 화면"을 오간다.
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
    roles = ["USER", "ADMIN"] if member and member.role == "ADMIN" else ["USER"]

    # 손님 묶음 먼저, 그 안에서 sort_order 순. (두 묶음 모두 sort_order 가 1부터라 role 로 먼저 나눈다)
    rows = db.scalars(
        select(Menu)
        .where(Menu.is_used == "Y", Menu.role.in_(roles))
        .order_by(Menu.role.desc(), Menu.sort_order, Menu.menu_id)
    ).all()
    nodes = {m.menu_id: MenuOut.model_validate(m) for m in rows}
    tree: list[MenuOut] = []
    for node in nodes.values():
        parent = nodes.get(node.parent_id) if node.parent_id else None
        (parent.children if parent else tree).append(node)
    return tree
