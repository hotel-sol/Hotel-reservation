from sqlalchemy import BigInteger, CHAR, ForeignKey, Integer, Unicode, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Menu(Base):
    """메뉴 (공통) — parent_id 가 NULL 이면 최상위 메뉴"""

    __tablename__ = "menu"

    menu_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("menu.menu_id"))
    menu_name: Mapped[str] = mapped_column(Unicode(50))
    menu_url: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(10), server_default="USER")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    is_used: Mapped[str] = mapped_column(CHAR(1), server_default="Y")
