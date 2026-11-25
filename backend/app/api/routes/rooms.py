"""객실 (손님) — ROOM-001 객실 추천, RSV-001 객실 정보"""
from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import text, update

from app.api.deps import DB, SessionCookie, member_from_cookie
from app.core.dates import today_kst
from app.schemas.room import RoomDetailOut
from app.services.room_service import room_detail
from app.core.exceptions import fail
from app.models import Room
from app.schemas.common import Page
from app.schemas.room import RecommendRoomOut, RoomOut, RoomSort
from app.services.room_service import recommend_rooms
from app.schemas.reservation import AvailableDatesOut, QuoteOut
from app.services.availability_service import month_range, room_calendar
from app.services.reservation_service import check_stay, get_bookable_room, night_price, total_price

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("/recommend", response_model=Page[RecommendRoomOut])
def recommend(
    db: DB,
    check_in: date | None = Query(None, alias="checkIn"),
    check_out: date | None = Query(None, alias="checkOut"),
    guests: int | None = Query(None, ge=1),
    sort: RoomSort = "recommend",
    page: int = Query(1, ge=1, le=10000),  # 아주 큰 값이면 OFFSET 범위를 넘어 500 → 상한
    size: int = Query(6, ge=1, le=50),
):
    if (check_in is None) != (check_out is None):
        fail(400, "INVALID_DATES", "체크인과 체크아웃을 함께 입력하세요.")
    if check_in and check_in < today_kst():
        fail(400, "INVALID_DATES", "지난 날짜는 선택할 수 없습니다.")
    if check_in and check_out and check_out <= check_in:
        fail(400, "INVALID_DATES", "체크아웃은 체크인 다음 날부터 선택할 수 있습니다.")
    items, total = recommend_rooms(
        db, check_in=check_in, check_out=check_out, guests=guests, sort=sort, page=page, size=size
    )
    return Page(items=items, total=total, page=page, size=size)


@router.get("/{room_id}", response_model=RoomDetailOut)
def get_room(room_id: int, db: DB):
    """객실 상세(1B) · 예약 화면(RSV-001) 객실 정보. RoomOut 에 사진 · 뱃지 · 예약 수를 더했다."""
    room = db.get(Room, room_id)
    if room is None or room.is_active != "Y":
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    return room_detail(db, room)


@router.post("/{room_id}/view", status_code=204)
def increase_view(room_id: int, db: DB, hotel_session: SessionCookie = None):
    """조회수(1-A1): 같은 사람 · 같은 방 · 같은 날(한국 날짜)은 1번만 센다. room.view_count 는 뜻 그대로(2번 화면이 읽음).
    회원은 M:<member_id> 로 한 사람씩. 비회원은 모두 합쳐 "G" 하나로 센다(방마다 하루 최대 +1):
    번호표 쿠키로 나누면 쿠키를 버리고 계속 부르는 프로그램이 무한히 올릴 수 있어서(#67-2)."""
    room = db.get(Room, room_id)
    if room is None or room.is_active != "Y":
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    member = member_from_cookie(db, hotel_session)
    viewer = f"M:{member.member_id}" if member is not None else "G"
    first = db.execute(
        text("INSERT INTO room_view (room_id, viewer_key, view_date) VALUES (:r, :v, :d) ON CONFLICT DO NOTHING"),
        {"r": room_id, "v": viewer, "d": today_kst()},
    ).rowcount
    if first:  # 오늘 처음 본 사람일 때만 +1 (UPDATE 한 줄로 올려서 동시에 눌러도 안 빠짐)
        db.execute(update(Room).where(Room.room_id == room_id).values(view_count=Room.view_count + 1))
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
    if not 2000 <= year <= 2100:  # 0000 년 등은 날짜로 만들 수 없어 500 이 났다
        fail(400, "INVALID_MONTH", "연도는 2000~2100 사이로 입력하세요.")
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
        price_per_night=night_price(room),
        total_price=total_price(room, nights),
    )