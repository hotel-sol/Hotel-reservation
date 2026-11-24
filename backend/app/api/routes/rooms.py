"""객실 (손님) — ROOM-001 객실 추천, RSV-001 객실 정보"""
from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import DB
from app.core.exceptions import fail
from app.models import Room
from app.schemas.common import Page
from app.schemas.room import RecommendRoomOut, RoomOut, RoomSort
from app.services.room_service import recommend_rooms
from app.core.dates import today_kst
from app.schemas.reservation import AvailableDatesOut, QuoteOut
from app.services.availability_service import month_range, room_calendar
from app.services.reservation_service import check_stay, get_bookable_room, total_price

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("/recommend", response_model=Page[RecommendRoomOut])
def recommend(
    db: DB,
    check_in: date | None = Query(None, alias="checkIn"),
    check_out: date | None = Query(None, alias="checkOut"),
    guests: int | None = Query(None, ge=1),
    sort: RoomSort = "recommend",
    page: int = Query(1, ge=1),
    size: int = Query(6, ge=1, le=50),
):
    if (check_in is None) != (check_out is None):
        fail(400, "INVALID_DATES", "체크인과 체크아웃을 함께 입력하세요.")
    if check_in and check_out and check_out <= check_in:
        fail(400, "INVALID_DATES", "체크아웃은 체크인 다음 날부터 선택할 수 있습니다.")
    items, total = recommend_rooms(
        db, check_in=check_in, check_out=check_out, guests=guests, sort=sort, page=page, size=size
    )
    return Page(items=items, total=total, page=page, size=size)


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int, db: DB):
    room = db.get(Room, room_id)
    if room is None or room.is_active != "Y":
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    return room


@router.post("/{room_id}/view", status_code=204)
def increase_view(room_id: int, db: DB):
    room = db.get(Room, room_id)
    if room is None:
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    room.view_count += 1
    db.commit()


@router.get("/{room_id}/available-dates", response_model=AvailableDatesOut)
def available_dates(room_id: int, db: DB, month: str = Query(..., pattern=r"^\d{4}-\d{2}$")):
    """RSV-001 예약 달력: month(예: 2026-12)의 날짜별 예약 가능 여부"""
    room = db.get(Room, room_id)
    if room is None or room.is_active != "Y":
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    year, mon = (int(x) for x in month.split("-"))
    if not 1 <= mon <= 12:
        fail(400, "INVALID_MONTH", "월은 01~12 사이로 입력하세요.")
    first, last = month_range(year, mon)
    return AvailableDatesOut(
        month=month,
        today=today_kst(),
        days=room_calendar(db, room_id, first, last),
    )


@router.get("/{room_id}/quote", response_model=QuoteOut)
def quote(
    room_id: int,
    db: DB,
    check_in: date = Query(..., alias="checkIn"),
    check_out: date = Query(..., alias="checkOut"),
    guests: int = Query(..., ge=1),
):
    """Step 2 4C 요금 견적: 예약 저장과 같은 확인 · 계산으로 박수 · 1박 요금 · 총액을 미리 보여 준다."""
    room = get_bookable_room(db, room_id)
    nights = check_stay(room, check_in, check_out, guests)
    return QuoteOut(
        room_id=room.room_id,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        nights=nights,
        price_per_night=room.price,
        total_price=total_price(room, nights),
    )