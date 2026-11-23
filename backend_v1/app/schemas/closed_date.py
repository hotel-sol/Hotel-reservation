from datetime import date

from pydantic import Field

from app.schemas.common import CamelModel


class ClosedDateCreate(CamelModel):
    room_id: int | None = None  # None = 호텔 전체 휴무
    closed_date: date
    reason: str | None = Field(default=None, max_length=200)


class ClosedDateOut(CamelModel):
    closed_date_id: int
    room_id: int | None
    closed_date: date
    reason: str | None
