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
    status: str
    request_memo: str | None
    created_at: datetime
    updated_at: datetime
