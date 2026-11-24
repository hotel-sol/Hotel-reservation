"""관리자) 예약 일자(휴무일) 관리 — ADM-002

GET    /admin/closed-dates?month=&roomId=                    그달 휴무일 (④ 목록 · 달력 표시)
GET    /admin/closed-dates/reservation-counts?month=&roomId= 날짜별 예약 수 {"2026-12-15": 1} (② 달력 "예약 N")
GET    /admin/closed-dates/available-rooms?month=            날짜별 남은 객실 수 {"2026-12-01": 40, ...} (전체 객실 달력, #30)
POST   /admin/closed-dates                                   휴무 지정
POST   /admin/closed-dates/range                             휴무 기간 지정 (Step 2 3A, 최대 31일, 전부 아니면 전무)
DELETE /admin/closed-dates/range?startDate=&endDate=&roomId= 휴무 기간 해제 (#28, 같은 범위에 직접 지정된 휴무만)
DELETE /admin/closed-dates/{closedDateId}                    휴무 해제

규칙 (기획문서에 없어서 정함)
- "그날 예약" = 그날 밤 묵는 대기 · 승인 예약 (체크인 ≤ 그날 < 체크아웃). 체크아웃 날은 비어 있다.
- 예약이 1건이라도 있으면 지정 불가: "이 날짜에 예약 N건이 있습니다. 먼저 예약을 취소해 주세요."
- 호텔 전체 휴무는 모든 방 예약을, 방 휴무는 그 방 예약만 본다.
- 호텔 전체 휴무인 날에 방 휴무 추가 → ALREADY_CLOSED. 방 휴무가 있는 날에 호텔 전체 휴무는 가능.
- 지난 날짜도 지정 · 해제 가능(#32 팀 결정: 잘못 넣은 기록을 고칠 수 있게). 사유 필수.
- 기간 지정이 막히면 막힌 날짜를 모두 알려 준다(#29, detail.blockedDates).
"""
import calendar
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, require_admin
from app.core.exceptions import fail
from app.models import ClosedDate, Reservation, Room
from app.models.reservation import LIVE_STATUSES
from app.schemas.closed_date import ClosedDateCreate, ClosedDateOut, ClosedDateRangeCreate

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


@router.get("/available-rooms", response_model=dict[str, int])
def available_rooms(db: DB, month: str = MonthQuery):
    """날짜별 남은 객실 수(#30) = 사용 중 객실 − 그날 휴무 객실 − 그날 숙박 중인 객실. 호텔 전체 휴무일은 0.
    비활성 객실의 휴무 · 예약은 세지 않는다."""
    first, last = month_range(month)
    active = set(db.scalars(select(Room.room_id).where(Room.is_active == "Y")))
    closures = db.execute(
        select(ClosedDate.room_id, ClosedDate.closed_date).where(ClosedDate.closed_date.between(first, last))
    ).all()
    stays = db.execute(
        select(Reservation.room_id, Reservation.check_in_date, Reservation.check_out_date).where(
            *live_stays(None), Reservation.check_in_date <= last, Reservation.check_out_date > first
        )
    ).all()
    hotel_days = {d for r, d in closures if r is None}
    result: dict[str, int] = {}
    day = first
    while day <= last:
        if day in hotel_days:
            result[day.isoformat()] = 0
        else:
            off = {r for r, d in closures if d == day} | {r for r, cin, cout in stays if cin <= day < cout}
            result[day.isoformat()] = len(active - off)
        day += timedelta(days=1)
    return result


MAX_RANGE_DAYS = 31


def check_input(db: DB, room_id: int | None, reason: str) -> tuple[str, Room | None]:
    """사유 · 객실 존재 검사. (다듬은 사유, 객실) 반환."""
    reason = reason.strip()
    if not reason:
        fail(400, "INVALID_INPUT", "휴무 사유를 입력해 주세요.")
    room = db.get(Room, room_id) if room_id is not None else None
    if room_id is not None and room is None:
        fail(404, "NOT_FOUND", "없는 객실입니다.")
    return reason, room


def blocked_reason(db: DB, room_id: int | None, day: date) -> tuple[str, int] | None:
    """그날 휴무로 지정할 수 없으면 (코드, 예약 수), 지정할 수 있으면 None."""
    # 이미 휴무: 호텔 전체 휴무가 있거나 같은 방이 이미 휴무.
    same_day = [ClosedDate.closed_date == day, ClosedDate.room_id.is_(None)]
    if room_id is not None:
        same_day[1] = or_(ClosedDate.room_id.is_(None), ClosedDate.room_id == room_id)
    if db.scalar(select(ClosedDate.closed_date_id).where(*same_day)) is not None:
        return "ALREADY_CLOSED", 0

    n = db.scalar(
        select(func.count()).where(
            *live_stays(room_id), Reservation.check_in_date <= day, Reservation.check_out_date > day
        )
    )
    return ("CLOSED_DATE_CONFLICT", n) if n else None


def blocked_message(where: str, code: str, n: int) -> str:
    if code == "ALREADY_CLOSED":
        return f"{where}{'은' if where.endswith('일') else '는'} 이미 휴무로 지정되어 있습니다."
    return f"{where}에 예약 {n}건이 있습니다. 먼저 예약을 취소해 주세요."


def day_list(days: list[date]) -> str:
    """[12/15, 12/17, 1/2] → "12월 15일 · 17일 · 1월 2일" (같은 달이면 월을 한 번만)"""
    parts, month = [], None
    for d in days:
        parts.append(f"{d.day}일" if d.month == month else f"{d.month}월 {d.day}일")
        month = d.month
    return " · ".join(parts)


def fail_blocked(blocked: list[tuple[date, str, int]]) -> None:
    """기간 지정에서 막힌 날짜를 모두 알려 준다(#29). 하나면 기존 문구 그대로."""
    extra = {"blockedDates": [{"date": d.isoformat(), "code": c, "reservationCount": n} for d, c, n in blocked]}
    if len(blocked) == 1:
        d, code, n = blocked[0]
        fail(409, code, blocked_message(f"{d.month}월 {d.day}일", code, n), **extra)
    booked = [d for d, c, _ in blocked if c == "CLOSED_DATE_CONFLICT"]
    closed = [d for d, c, _ in blocked if c == "ALREADY_CLOSED"]
    msg = []
    if booked:
        msg.append(f"{day_list(booked)}에 예약이 있습니다.")
    if closed:
        msg.append(f"{day_list(closed)}은 이미 휴무입니다.")
    if booked:
        msg.append("먼저 예약을 취소해 주세요.")
    fail(409, "CLOSED_DATE_CONFLICT" if booked else "ALREADY_CLOSED", " ".join(msg), **extra)


def save(db: DB, rows: list[ClosedDate]) -> None:
    db.add_all(rows)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        fail(409, "ALREADY_CLOSED", "이미 휴무로 지정된 날짜입니다.")
    for row in rows:
        db.refresh(row)


@router.post("", response_model=ClosedDateOut, status_code=201)
def create_closed_date(body: ClosedDateCreate, db: DB):
    reason, room = check_input(db, body.room_id, body.reason)
    if b := blocked_reason(db, body.room_id, body.closed_date):
        code, n = b
        fail(409, code, blocked_message("이 날짜", code, n), **({"reservationCount": n} if n else {}))
    row = ClosedDate(room_id=body.room_id, closed_date=body.closed_date, reason=reason)
    save(db, [row])
    return to_out(row, room.room_name if room else None)


@router.post("/range", response_model=list[ClosedDateOut], status_code=201)
def create_closed_date_range(body: ClosedDateRangeCreate, db: DB):
    """기간 지정(3A): 날짜마다 1행. 하루라도 막히면 아무것도 넣지 않는다."""
    if body.end_date < body.start_date:
        fail(400, "INVALID_INPUT", "끝 날짜가 시작 날짜보다 빠릅니다.")
    days = (body.end_date - body.start_date).days + 1
    if days > MAX_RANGE_DAYS:
        fail(400, "RANGE_TOO_LONG", f"기간은 최대 {MAX_RANGE_DAYS}일까지 지정할 수 있습니다. (지금 {days}일)")
    reason, room = check_input(db, body.room_id, body.reason)

    dates = [body.start_date + timedelta(days=i) for i in range(days)]
    blocked = [(day, *b) for day in dates if (b := blocked_reason(db, body.room_id, day))]
    if blocked:
        fail_blocked(blocked)
    rows = [ClosedDate(room_id=body.room_id, closed_date=day, reason=reason) for day in dates]
    save(db, rows)
    name = room.room_name if room else None
    return [to_out(row, name) for row in rows]


@router.delete("/range")
def delete_closed_date_range(
    db: DB,
    start_date: date = Query(..., alias="startDate"),
    end_date: date = Query(..., alias="endDate"),
    room_id: int | None = RoomQuery,
) -> dict[str, int]:
    """기간 해제(#28): 같은 범위(roomId 없음 = 호텔 전체, 있음 = 그 방)에 직접 지정된 휴무만 지운다."""
    if end_date < start_date:
        fail(400, "INVALID_INPUT", "끝 날짜가 시작 날짜보다 빠릅니다.")
    scope = ClosedDate.room_id.is_(None) if room_id is None else ClosedDate.room_id == room_id
    rows = db.scalars(select(ClosedDate).where(scope, ClosedDate.closed_date.between(start_date, end_date))).all()
    if not rows:
        fail(404, "NOT_FOUND", "이 기간에 해제할 휴무가 없습니다.")
    for row in rows:
        db.delete(row)
    db.commit()
    return {"deleted": len(rows)}


@router.delete("/{closed_date_id}", status_code=204)
def delete_closed_date(closed_date_id: int, db: DB):
    row = db.get(ClosedDate, closed_date_id) or fail(404, "NOT_FOUND", "없는 휴무일입니다.")
    db.delete(row)
    db.commit()
