from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel

RoomSort = Literal["recommend", "popular", "price"]


class RoomOut(CamelModel):
    room_id: int
    room_name: str
    room_type: str
    max_guest: int
    price: int
    description: str | None
    view_count: int
    is_active: str


class RecommendRoomOut(RoomOut):
    score: float = 0
    recent_reservations: int = 0  # 최근 30일 예약 수 (대기 + 승인)
    total_reservations: int = 0  # 전체 예약 수 (인기순 기준)
    is_recommended: bool = False  # 1등에 "추천" 표시
    thumbnail_url: str | None = None


class RoomCreate(CamelModel):
    room_name: str = Field(min_length=1, max_length=100)
    room_type: str = Field(min_length=1, max_length=50)
    max_guest: int = Field(ge=1)
    price: int = Field(gt=0)
    description: str | None = Field(default=None, max_length=1000)


class RoomUpdate(RoomCreate):
    pass


class RoomStatusUpdate(CamelModel):
    is_active: Literal["Y", "N"]
