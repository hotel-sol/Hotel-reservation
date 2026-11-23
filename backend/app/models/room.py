from datetime import datetime

from sqlalchemy import BigInteger, CHAR, DateTime, Integer, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Room(Base):
    """객실 — 삭제하지 않고 is_active='N' 으로 비활성화"""

    __tablename__ = "room"

    room_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    room_name: Mapped[str] = mapped_column(Unicode(100), unique=True)
    room_type: Mapped[str] = mapped_column(Unicode(50))
    max_guest: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Unicode(1000))
    view_count: Mapped[int] = mapped_column(Integer, server_default="0")
    is_active: Mapped[str] = mapped_column(CHAR(1), server_default="Y")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
