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


class RoomSummary(CamelModel):
    """객실 관리 목록 요약 (ADM-001, 2A). 휴무는 예약 일자 관리(closed_date)를 그대로 쓴다 — 판매중지 흡수(11-23).

    API 명세서 v1.3 summary(onSale · blockedNow · blockedSoon)와 같은 뜻:
    on_sale = 사용 중이고 오늘 휴무가 아닌 객실(휴무 예정 포함), closed_today = blockedNow, closed_soon = blockedSoon.
    """

    total: int
    on_sale: int
    closed_today: int
    closed_soon: int
    inactive: int
    closed_today_room_ids: list[int]  # 목록 상태 칸에 "오늘 휴무" 표시용
    closed_soon_room_ids: list[int]  # "휴무 예정" 표시용
