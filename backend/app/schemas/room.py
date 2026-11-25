from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.common import CamelModel

RoomSort = Literal["recommend", "popular", "price"]
RoomBadge = Literal["BEST", "HOT", "NEW"]
ViewType = Literal["RIVER", "CITY", "MOUNTAIN"]  # 리버뷰 · 시티뷰 · 마운틴뷰

# #76-1·2: 앞뒤 공백을 먼저 지우고 길이를 잰다 → "   " 는 422, "0775호 " 는 "0775호" 로 저장(중복 검사도 그 이름으로)
RoomName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
RoomType = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


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
    room_name: RoomName
    room_type: RoomType
    # 상한 (#69): 요금이 너무 크면 30박 총액이 reservation.total_price(INT) 한도를 넘어 예약 저장이 500,
    # 2^31 이상이면 객실 저장 자체가 500. 가장 비싼 로얄 스위트 성수기 리버뷰도 5,720,000원 · 최대 6명
    max_guest: int = Field(ge=1, le=20)
    price: int = Field(gt=0, le=10_000_000)
    description: str | None = Field(default=None, max_length=1000)
    # 2-A1: 등급을 주면 서버가 room_type 을 등급 이름으로 맞춘다. 안 주면 예전처럼 room_type 글자 그대로
    grade_id: int | None = None
    view_type: ViewType | None = None
    bed_type: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None


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
