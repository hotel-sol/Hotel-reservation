"""관리자) 예약 관리 — ADM-003

상태 전이: PENDING → APPROVED/CANCELED, APPROVED → CANCELED, CANCELED → (불가)
체크인이 지난 예약은 취소 불가. 변경 시 updated_at 기록.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select

from app.api.deps import DB, require_admin
from app.core.exceptions import fail
from app.models import Member, Reservation, Room
from app.models.reservation import APPROVED, CANCELED, PENDING
from app.schemas.common import Page
from app.schemas.reservation import ReservationOut

router = APIRouter(
    prefix="/admin/reservations", tags=["admin: reservations"], dependencies=[Depends(require_admin)]
)


@router.get("", response_model=Page[ReservationOut])
def list_reservations(
    db: DB,
    # 생략하면 전체. 화면 기본 탭(승인 대기)은 프론트가 status=PENDING 으로 보낸다.
    status: str | None = Query(None, pattern="^(PENDING|APPROVED|CANCELED)$"),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    q = (
        select(Reservation, Room.room_name, Member.name)
        .join(Room, Room.room_id == Reservation.room_id)
        .join(Member, Member.member_id == Reservation.member_id)
    )
    if status:
        q = q.where(Reservation.status == status)
    if from_date:
        q = q.where(Reservation.check_in_date >= from_date)
    if to_date:
        q = q.where(Reservation.check_in_date <= to_date)
    if keyword:
        cond = Member.name.contains(keyword)
        if keyword.isdigit():
            cond = or_(cond, Reservation.reservation_id == int(keyword))
        q = q.where(cond)

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.execute(q.order_by(Reservation.reservation_id.desc()).offset((page - 1) * size).limit(size)).all()
    items = []
    for r, room_name, member_name in rows:
        out = ReservationOut.model_validate(r)
        out.room_name, out.member_name = room_name, member_name
        items.append(out)
    return Page(items=items, total=total, page=page, size=size)


def _change_status(db, reservation_id: int, to: str) -> Reservation:
    r = db.get(Reservation, reservation_id) or fail(404, "RESERVATION_NOT_FOUND", "예약을 찾을 수 없습니다.")
    allowed = {PENDING: {APPROVED, CANCELED}, APPROVED: {CANCELED}, CANCELED: set()}
    if to not in allowed[r.status]:
        fail(409, "INVALID_STATUS", f"{r.status} 상태에서는 {to}(으)로 바꿀 수 없습니다.")
    if to == CANCELED and r.check_in_date < date.today():
        fail(409, "PAST_CHECK_IN", "체크인이 지난 예약은 취소할 수 없습니다.")
    r.status = to
    r.updated_at = datetime.now()
    db.commit()
    return r


@router.patch("/{reservation_id}/approve", response_model=ReservationOut)
def approve(reservation_id: int, db: DB):
    return _change_status(db, reservation_id, APPROVED)


@router.patch("/{reservation_id}/cancel", response_model=ReservationOut)
def cancel(reservation_id: int, db: DB):
    return _change_status(db, reservation_id, CANCELED)
