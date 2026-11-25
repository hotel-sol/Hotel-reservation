from datetime import date, datetime

from pydantic import Field, model_validator

from app.schemas.common import CamelModel


class ReservationCreate(CamelModel):
    room_id: int
    check_in_date: date
    check_out_date: date
    guest_count: int = Field(ge=1)
    request_memo: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def check_dates(self):
        if self.check_out_date <= self.check_in_date:
            raise ValueError("체크아웃은 체크인 다음 날부터 선택할 수 있습니다.")
        return self


class ReservationOut(CamelModel):
    reservation_id: int
    member_id: int
    room_id: int
    room_name: str | None = None
    member_name: str | None = None
    check_in_date: date
    check_out_date: date
    guest_count: int
    total_price: int
    price_per_night: int | None = None  # 4-A3. 비어 있는 옛 예약이 있을 수 있음(#60 R5)
    status: str
    request_memo: str | None
    canceled_at: datetime | None = None
    canceled_by: int | None = None  # 취소한 회원 번호 (관리자 취소면 그 관리자)
    created_at: datetime
    updated_at: datetime


class CalendarDay(CamelModel):
    """예약 달력 하루 (RSV-001). reason: PAST · CLOSED · BOOKED, 예약 가능하면 None"""

    day: date
    available: bool
    reason: str | None = None


class QuoteOut(CamelModel):
    """GET /api/rooms/{id}/quote 응답 (Step 2 4C). 예약 저장 때와 같은 계산: total_price = price_per_night * nights"""

    room_id: int
    check_in: date
    check_out: date
    guests: int
    nights: int
    price_per_night: int
    total_price: int


class AvailableDatesOut(CamelModel):
    """GET /api/rooms/{id}/available-dates 응답"""

    month: str
    today: date
    days: list[CalendarDay]