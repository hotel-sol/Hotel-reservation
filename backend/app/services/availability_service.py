"""예약 달력 (RSV-001) · 예약 막힘 확인 (Step 2 4A).

예약이 차지하는 날: 체크인 <= 날짜 < 체크아웃 (체크아웃 날은 비어 있음)
막히는 이유: PAST(지난 날짜) > CLOSED(휴무일) > BOOKED(예약된 날) 순서로 하나만 표시
"""
import calendar
from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.dates import today_kst
from app.models import ClosedDate, Reservation
from app.models.reservation import LIVE_STATUSES
from app.schemas.reservation import CalendarDay

PAST, CLOSED, BOOKED = "PAST", "CLOSED", "BOOKED"
DATE_CLOSED, ROOM_CLOSED = "DATE_CLOSED", "ROOM_CLOSED"


def month_range(year: int, month: int) -> tuple[date, date]:
    """그달의 1일과 마지막 날."""
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return first, last


def room_calendar(db: Session, room_id: int, first: date, last: date) -> list[CalendarDay]:
    """first ~ last 사이 날짜마다 예약 가능 여부를 돌려준다."""
    # 1) 휴무일: 이 방만 쉬는 날 + 호텔 전체가 쉬는 날(room_id 가 비어 있음)
    closed = set(
        db.scalars(
            select(ClosedDate.closed_date).where(
                or_(ClosedDate.room_id == room_id, ClosedDate.room_id.is_(None)),
                ClosedDate.closed_date >= first,
                ClosedDate.closed_date <= last,
            )
        )
    )

    # 2) 예약된 날: 이 달과 겹치는 살아 있는 예약(대기 · 승인)
    rows = db.execute(
        select(Reservation.check_in_date, Reservation.check_out_date).where(
            Reservation.room_id == room_id,
            Reservation.status.in_(LIVE_STATUSES),
            Reservation.check_in_date <= last,
            Reservation.check_out_date > first,
        )
    ).all()
    booked: set[date] = set()
    for check_in, check_out in rows:
        d = max(check_in, first)
        end = min(check_out, last + timedelta(days=1))  # 체크아웃 날은 제외
        while d < end:
            booked.add(d)
            d += timedelta(days=1)

    # 3) 하루씩 이유 붙이기
    today = today_kst()
    days: list[CalendarDay] = []
    d = first
    while d <= last:
        if d < today:
            reason = PAST
        elif d in closed:
            reason = CLOSED
        elif d in booked:
            reason = BOOKED
        else:
            reason = None
        days.append(CalendarDay(day=d, available=reason is None, reason=reason))
        d += timedelta(days=1)
    return days


def block_reason(db: Session, room_id: int, check_in: date, check_out: date) -> str | None:
    """예약하려는 기간 [check_in, check_out)이 막힌 이유. 막히지 않았으면 None.

    DATE_CLOSED: 호텔 전체 휴무 / ROOM_CLOSED: 이 객실만 판매 중지 / BOOKED: 다른 예약과 겹침
    """
    in_range = (ClosedDate.closed_date >= check_in, ClosedDate.closed_date < check_out)

    hotel_closed = select(ClosedDate.closed_date).where(ClosedDate.room_id.is_(None), *in_range).limit(1)
    if db.scalar(hotel_closed) is not None:
        return DATE_CLOSED

    room_closed = select(ClosedDate.closed_date).where(ClosedDate.room_id == room_id, *in_range).limit(1)
    if db.scalar(room_closed) is not None:
        return ROOM_CLOSED

    overlap = (
        select(Reservation.reservation_id)
        .where(
            Reservation.room_id == room_id,
            Reservation.status.in_(LIVE_STATUSES),
            Reservation.check_in_date < check_out,
            Reservation.check_out_date > check_in,
        )
        .limit(1)
    )
    if db.scalar(overlap) is not None:
        return BOOKED
    return None