from datetime import date

from pydantic import Field

from app.schemas.common import CamelModel


class ClosedDateCreate(CamelModel):
    room_id: int | None = None  # None = 호텔 전체 휴무
    closed_date: date
    reason: str = Field(min_length=1, max_length=200)  # 화면 ③ "휴무 사유" (필수)


class ClosedDateRangeCreate(CamelModel):
    """Step 2 3A 휴무 기간 지정: start ~ end(포함), 최대 31일."""
    room_id: int | None = None  # None = 호텔 전체 휴무, 있으면 그 방 기간 판매 중지
    start_date: date
    end_date: date
    reason: str = Field(min_length=1, max_length=200)


class ClosedDateOut(CamelModel):
    closed_date_id: int
    room_id: int | None
    room_name: str | None = None  # 호텔 전체 휴무면 None
    closed_date: date
    reason: str | None
