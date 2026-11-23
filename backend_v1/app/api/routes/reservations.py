"""객실 예약 (손님) — RSV-001 예약하기, RSV-002 예약 완료"""
from sqlalchemy import select

from fastapi import APIRouter

from app.api.deps import DB, CurrentMember
from app.core.exceptions import fail
from app.models import Reservation, Room
from app.schemas.reservation import ReservationCreate, ReservationOut
from app.services.room_service import available_room_filter

router = APIRouter(prefix="/reservations", tags=["reservations"])


def to_out(r: Reservation, room_name: str | None = None) -> ReservationOut:
    out = ReservationOut.model_validate(r)
    out.room_name = room_name
    return out


@router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(body: ReservationCreate, member: CurrentMember, db: DB):
    room = db.get(Room, body.room_id)
    if room is None or room.is_active != "Y":
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    if body.guest_count > room.max_guest:
        fail(400, "TOO_MANY_GUESTS", f"최대 {room.max_guest}명까지 예약할 수 있습니다.")
    # TODO: 지난 날짜 차단, 동시 예약 경합 시 잠금(UPDLOCK) 처리
    available = db.scalar(
        select(Room.room_id).where(Room.room_id == room.room_id, available_room_filter(body.check_in_date, body.check_out_date))
    )
    if available is None:
        fail(409, "ROOM_NOT_AVAILABLE", "선택한 날짜에 예약할 수 없는 객실입니다.")

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
