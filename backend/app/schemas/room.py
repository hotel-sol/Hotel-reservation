from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel

RoomSort = Literal["recommend", "popular", "price"]
RoomBadge = Literal["BEST", "HOT", "NEW"]
ViewType = Literal["RIVER", "CITY", "MOUNTAIN"]  # 리버뷰 · 시티뷰 · 마운틴뷰


class RoomGradeOut(CamelModel):
    """객실 등급 (2-A1, GET /api/room-grades)"""

    grade_id: int
    grade_code: str
    grade_name: str
    base_price: int  # 비수기 · 시티/마운틴뷰 1박 요금 (리버뷰는 × 1.1)
    base_guest: int
    max_guest: int
    area_m2: int
    bed_type: str | None
    intro: str | None
    sort_order: int


class RoomOut(CamelModel):
    room_id: int
    room_name: str
    room_type: str
    max_guest: int
    price: int
    description: str | None
    view_count: int
    is_active: str
    # 2-A1 등급 · 전망 · 침대 (예전 객실은 null)
    grade_id: int | None = None
    view_type: str | None = None
    bed_type: str | None = None


class RecommendRoomOut(RoomOut):
    score: float = 0
    recent_reservations: int = 0  # 최근 30일 승인 예약 수
    total_reservations: int = 0  # 전체 승인 예약 수 (인기순 기준)
    is_recommended: bool = False  # 추천 점수 1~3위 = badge "BEST" ("★ 추천" 리본)
    badge: RoomBadge | None = None  # BEST > HOT(7일 승인 예약 1~3위) > NEW(등록 14일 이내), 하나만
    thumbnail_url: str | None = None


class RoomDetailOut(RecommendRoomOut):
    """객실 상세 (1B): 추천 카드 정보 + 사진 전부(올린 순서)"""
    photos: list[str] = []


class RoomCreate(CamelModel):
    room_name: str = Field(min_length=1, max_length=100)
    room_type: str = Field(min_length=1, max_length=50)
    max_guest: int = Field(ge=1)
    price: int = Field(gt=0)
    description: str | None = Field(default=None, max_length=1000)
    # 2-A1: 등급을 주면 서버가 room_type 을 등급 이름으로 맞춘다. 안 주면 예전처럼 room_type 글자 그대로
    grade_id: int | None = None
    view_type: ViewType | None = None
    bed_type: str | None = Field(default=None, max_length=30)


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
