"""객실 예약 (손님) — RSV-001 예약하기, RSV-002 예약 완료"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter

from app.api.deps import DB, CurrentMember
from app.core.exceptions import fail
from app.models import Reservation, Room
from app.schemas.reservation import ReservationCreate, ReservationOut
from app.services.availability_service import block_reason
from app.services.reservation_service import check_stay, get_bookable_room, total_price

router = APIRouter(prefix="/reservations", tags=["reservations"])

# 막힌 이유 → (상태코드, 오류 코드, 화면에 띄울 문장)
BLOCK_ERRORS = {
    "DATE_CLOSED": (409, "DATE_CLOSED", "선택한 기간에 호텔 휴무일이 있어 예약할 수 없습니다."),
    "ROOM_CLOSED": (409, "ROOM_CLOSED", "이 객실은 선택한 기간에 판매하지 않습니다."),
    "BOOKED": (409, "ROOM_NOT_AVAILABLE", "선택한 날짜에 이미 예약이 있습니다."),
}


EXCLUSION_VIOLATION = "23P01"  # PostgreSQL: EXCLUDE 제약 위반


def is_overlap_violation(e: IntegrityError) -> bool:
    """이중 예약 제약(ex_reservation_no_overlap, #57 4-A1 · #60 ③단계) 위반인지.

    reservation 에 걸리는 EXCLUDE 제약은 이것 하나뿐이라 SQLSTATE 만 본다.
    """
    return getattr(e.orig, "sqlstate", None) == EXCLUSION_VIOLATION


def to_out(r: Reservation, room_name: str | None = None) -> ReservationOut:
    out = ReservationOut.model_validate(r)
    out.room_name = room_name
    return out


@router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(body: ReservationCreate, member: CurrentMember, db: DB):
    # 객실 행을 잠가서, 같은 방에 동시에 들어온 예약은 먼저 온 쪽이 끝날 때까지 기다리게 한다.
    room = get_bookable_room(db, body.room_id, lock=True)
    nights = check_stay(room, body.check_in_date, body.check_out_date, body.guest_count)

    reason = block_reason(db, room.room_id, body.check_in_date, body.check_out_date)
    if reason is not None:
        fail(*BLOCK_ERRORS[reason])

    reservation = Reservation(
        member_id=member.member_id,
        room_id=room.room_id,
        check_in_date=body.check_in_date,
        check_out_date=body.check_out_date,
        guest_count=body.guest_count,
        total_price=total_price(room, nights),
        request_memo=body.request_memo,
    )
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        if is_overlap_violation(e):  # 위 확인을 지나친 겹침도 DB 제약(③단계)이 막는다
            fail(*BLOCK_ERRORS["BOOKED"])
        raise
    db.refresh(reservation)
    return to_out(reservation, room.room_name)


@router.get("/me", response_model=list[ReservationOut])
def my_reservations(member: CurrentMember, db: DB):
    rows = db.execute(
        select(Reservation, Room.room_name)
        .join(Room, Room.room_id == Reservation.room_id)
        .where(Reservation.member_id == member.member_id)
        .order_by(Reservation.reservation_id.desc())
    ).all()
    return [to_out(r, name) for r, name in rows]


@router.get("/{reservation_id}", response_model=ReservationOut)
def get_reservation(reservation_id: int, member: CurrentMember, db: DB):
    row = db.execute(
        select(Reservation, Room.room_name)
        .join(Room, Room.room_id == Reservation.room_id)
        .where(Reservation.reservation_id == reservation_id)
    ).first()
    if row is None or (row[0].member_id != member.member_id and member.role != "ADMIN"):
        fail(404, "RESERVATION_NOT_FOUND", "예약을 찾을 수 없습니다.")
    return to_out(*row)