"""객실 예약 (손님) — RSV-001 예약하기, RSV-002 예약 완료"""
from sqlalchemy import select

from fastapi import APIRouter

from app.api.deps import DB, CurrentMember
from app.core.dates import today_kst
from app.core.exceptions import fail
from app.models import Reservation, Room
from app.schemas.reservation import ReservationCreate, ReservationOut
from app.services.availability_service import block_reason

router = APIRouter(prefix="/reservations", tags=["reservations"])

# 막힌 이유 → (상태코드, 오류 코드, 화면에 띄울 문장)
BLOCK_ERRORS = {
    "DATE_CLOSED": (409, "DATE_CLOSED", "선택한 기간에 호텔 휴무일이 있어 예약할 수 없습니다."),
    "ROOM_CLOSED": (409, "ROOM_CLOSED", "이 객실은 선택한 기간에 판매하지 않습니다."),
    "BOOKED": (409, "ROOM_NOT_AVAILABLE", "선택한 날짜에 이미 예약이 있습니다."),
}


def to_out(r: Reservation, room_name: str | None = None) -> ReservationOut:
    out = ReservationOut.model_validate(r)
    out.room_name = room_name
    return out


@router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(body: ReservationCreate, member: CurrentMember, db: DB):
    # 객실 행을 잠가서, 같은 방에 동시에 들어온 예약은 먼저 온 쪽이 끝날 때까지 기다리게 한다.
    room = db.get(Room, body.room_id, with_for_update=True)
    if room is None or room.is_active != "Y":
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    if body.guest_count > room.max_guest:
        fail(400, "TOO_MANY_GUESTS", f"최대 {room.max_guest}명까지 예약할 수 있습니다.")
    if body.check_in_date < today_kst():
        fail(400, "PAST_DATE", "지난 날짜는 예약할 수 없습니다.")

    reason = block_reason(db, room.room_id, body.check_in_date, body.check_out_date)
    if reason is not None:
        fail(*BLOCK_ERRORS[reason])

    nights = (body.check_out_date - body.check_in_date).days
    reservation = Reservation(
        member_id=member.member_id,
        room_id=room.room_id,
        check_in_date=body.check_in_date,
        check_out_date=body.check_out_date,
        guest_count=body.guest_count,
        total_price=room.price * nights,
        request_memo=body.request_memo,
    )
    db.add(reservation)
    db.commit()
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