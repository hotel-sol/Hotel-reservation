"""관리자) 예약 일자(휴무일) 관리 — ADM-002

GET    /admin/closed-dates?month=&roomId=                    그달 휴무일 (④ 목록 · 달력 표시)
GET    /admin/closed-dates/reservation-counts?month=&roomId= 날짜별 예약 수 {"2026-12-15": 1} (② 달력 "예약 N")
POST   /admin/closed-dates                                   휴무 지정
DELETE /admin/closed-dates/{closedDateId}                    휴무 해제

규칙 (기획문서에 없어서 정함)
- "그날 예약" = 그날 밤 묵는 대기 · 승인 예약 (체크인 ≤ 그날 < 체크아웃). 체크아웃 날은 비어 있다.
- 예약이 1건이라도 있으면 지정 불가: "이 날짜에 예약 N건이 있습니다. 먼저 예약을 취소해 주세요."
- 호텔 전체 휴무는 모든 방 예약을, 방 휴무는 그 방 예약만 본다.
- 호텔 전체 휴무인 날에 방 휴무 추가 → ALREADY_CLOSED. 방 휴무가 있는 날에 호텔 전체 휴무는 가능.
- 오늘(한국 시간)부터 지정 가능. 사유 필수.
"""
import calendar
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, require_admin
from app.core.dates import today_kst
from app.core.exceptions import fail
from app.models import ClosedDate, Reservation, Room
from app.models.reservation import LIVE_STATUSES
from app.schemas.closed_date import ClosedDateCreate, ClosedDateOut

router = APIRouter(
    prefix="/admin/closed-dates", tags=["admin: closed-dates"], dependencies=[Depends(require_admin)]
)

MonthQuery = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-12"])
RoomQuery = Query(None, alias="roomId")


def month_range(month: str) -> tuple[date, date]:
    year, mon = map(int, month.split("-"))
    return date(year, mon, 1), date(year, mon, calendar.monthrange(year, mon)[1])


def to_out(row: ClosedDate, room_name: str | None) -> ClosedDateOut:
    out = ClosedDateOut.model_validate(row)
    out.room_name = room_name
    return out


def live_stays(room_id: int | None):
    """살아 있는 예약 조건. room_id가 있으면 그 방만."""
    conds = [Reservation.status.in_(LIVE_STATUSES)]
    if room_id is not None:
        conds.append(Reservation.room_id == room_id)
    return conds


@router.get("", response_model=list[ClosedDateOut])
def list_closed_dates(db: DB, month: str = MonthQuery, room_id: int | None = RoomQuery):
    """roomId 없음 = 모든 휴무. roomId 있음 = 호텔 전체 휴무 + 그 방 휴무."""
    first, last = month_range(month)
    q = (
        select(ClosedDate, Room.room_name)
        .outerjoin(Room, Room.room_id == ClosedDate.room_id)
        .where(ClosedDate.closed_date.between(first, last))
    )
    if room_id is not None:
        q = q.where(or_(ClosedDate.room_id.is_(None), ClosedDate.room_id == room_id))
    rows = db.execute(q.order_by(ClosedDate.closed_date, ClosedDate.room_id)).all()
    return [to_out(row, name) for row, name in rows]


@router.get("/reservation-counts", response_model=dict[str, int])
def reservation_counts(db: DB, month: str = MonthQuery, room_id: int | None = RoomQuery):
    """날짜별 예약 수(대기 + 승인). 0건인 날은 빠진다."""
    first, last = month_range(month)
    stays = db.execute(
        select(Reservation.check_in_date, Reservation.check_out_date).where(
            *live_stays(room_id), Reservation.check_in_date <= last, Reservation.check_out_date > first
        )
    ).all()
    counts: dict[str, int] = {}
    day = first
    while day <= last:
        n = sum(1 for check_in, check_out in stays if check_in <= day < check_out)
        if n:
            counts[day.isoformat()] = n
        day += timedelta(days=1)
    return counts


@router.post("", response_model=ClosedDateOut, status_code=201)
def create_closed_date(body: ClosedDateCreate, db: DB):
    reason = body.reason.strip()
    if not reason:
        fail(400, "INVALID_INPUT", "휴무 사유를 입력해 주세요.")
    if body.closed_date < today_kst():
        fail(400, "PAST_DATE", "지난 날짜는 휴무로 지정할 수 없습니다.")
    room = db.get(Room, body.room_id) if body.room_id is not None else None
    if body.room_id is not None and room is None:
        fail(404, "NOT_FOUND", "없는 객실입니다.")

    # 이미 휴무: 호텔 전체 휴무가 있거나 같은 방이 이미 휴무.
    # DB UNIQUE(room_id, closed_date)는 room_id가 NULL이면 중복을 막지 못해서 여기서 검사한다.
    # ponytail: 호텔 전체 휴무를 같은 순간에 두 번 넣으면 둘 다 들어갈 수 있다. 문제 되면 행 잠금.
    same_day = [ClosedDate.closed_date == body.closed_date, ClosedDate.room_id.is_(None)]
    if body.room_id is not None:
        same_day[1] = or_(ClosedDate.room_id.is_(None), ClosedDate.room_id == body.room_id)
    if db.scalar(select(ClosedDate.closed_date_id).where(*same_day)) is not None:
        fail(409, "ALREADY_CLOSED", "이미 휴무로 지정된 날짜입니다.")

    n = db.scalar(
        select(func.count()).where(
            *live_stays(body.room_id),
            Reservation.check_in_date <= body.closed_date,
            Reservation.check_out_date > body.closed_date,
        )
    )
    if n:
        fail(409, "CLOSED_DATE_CONFLICT", f"이 날짜에 예약 {n}건이 있습니다. 먼저 예약을 취소해 주세요.",
             reservationCount=n)

    row = ClosedDate(room_id=body.room_id, closed_date=body.closed_date, reason=reason)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        fail(409, "ALREADY_CLOSED", "이미 휴무로 지정된 날짜입니다.")
    db.refresh(row)
    return to_out(row, room.room_name if room else None)


@router.delete("/{closed_date_id}", status_code=204)
def delete_closed_date(closed_date_id: int, db: DB):
    row = db.get(ClosedDate, closed_date_id) or fail(404, "NOT_FOUND", "없는 휴무일입니다.")
    db.delete(row)
    db.commit()
