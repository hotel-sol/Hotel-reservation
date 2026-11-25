from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClosedDate(Base):
    """휴무일 — room_id 가 NULL 이면 호텔 전체 휴무"""

    __tablename__ = "closed_date"

    closed_date_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    room_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("room.room_id"))
    closed_date: Mapped[date] = mapped_column(Date)
    closure_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("closure.closure_id", ondelete="CASCADE"))  # 사유는 묶음에
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
