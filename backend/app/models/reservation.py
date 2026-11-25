from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Unicode, String, func
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
    # 4-A3 예약 때의 1박 요금. ③단계 전까지는 비어 있는 옛 예약이 있을 수 있다(#60 R5).
    price_per_night: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), server_default=PENDING)
    request_memo: Mapped[str | None] = mapped_column(Unicode(200))
    # 4-A4 취소 기록: 언제 · 누가(member_id, 손님 본인 또는 관리자) 취소했는지
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime)
    canceled_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("member.member_id"))
    cancel_reason: Mapped[str | None] = mapped_column(Unicode(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # DB마다 자동 갱신(ON UPDATE) 지원이 달라서 상태 변경 코드에서 updated_at 을 직접 넣는다.
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
