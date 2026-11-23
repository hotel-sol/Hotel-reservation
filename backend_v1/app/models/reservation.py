from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, NVARCHAR, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PENDING, APPROVED, CANCELED = "PENDING", "APPROVED", "CANCELED"
LIVE_STATUSES = (PENDING, APPROVED)  # 객실을 잡고 있는 예약


class Reservation(Base):
    """객실 예약 — PENDING(대기) → APPROVED(승인) / CANCELED(취소)"""

    __tablename__ = "reservation"

    reservation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("member.member_id"))
    room_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("room.room_id"))
    check_in_date: Mapped[date] = mapped_column(Date)
    check_out_date: Mapped[date] = mapped_column(Date)
    guest_count: Mapped[int] = mapped_column(Integer)
    total_price: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), server_default=PENDING)
    request_memo: Mapped[str | None] = mapped_column(NVARCHAR(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.getdate())
    # MSSQL 은 ON UPDATE 가 없으므로 상태 변경 시 코드에서 updated_at 을 직접 넣는다.
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.getdate())
