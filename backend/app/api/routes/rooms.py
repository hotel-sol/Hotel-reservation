"""객실 (손님) — ROOM-001 객실 추천, RSV-001 객실 정보"""
from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import DB
from app.core.dates import today_kst
from app.schemas.room import RoomDetailOut
from app.services.room_service import room_detail
from app.core.exceptions import fail
from app.models import Room
from app.schemas.common import Page
from app.schemas.room import RecommendRoomOut, RoomOut, RoomSort
from app.services.room_service import recommend_rooms

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
def increase_view(room_id: int, db: DB):
    room = db.get(Room, room_id)
    if room is None or room.is_active != "Y":
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    room.view_count += 1
    db.commit()


@router.get("/{room_id}/available-dates")
def available_dates(room_id: int, db: DB, month: str = Query(..., pattern=r"^\d{4}-\d{2}$")):
    # TODO(RSV-001): month 의 날짜별 선택 가능 여부 (지난 날짜 · 휴무일 · 예약된 날짜 제외)
    fail(501, "NOT_IMPLEMENTED", "준비 중입니다.")
