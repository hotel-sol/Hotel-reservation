from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel

# 3-A2 사유 분류. 공사 · 점검 · 행사 · 휴관 · 기타 (models/closure.py REASON_CODES 와 같은 값)
ReasonCode = Literal["CONSTRUCTION", "MAINTENANCE", "EVENT", "CLOSURE", "ETC"]
ClosureStatus = Literal["SCHEDULED", "ACTIVE", "ENDED"]  # 예정 · 진행 중 · 종료


class ClosedDateCreate(CamelModel):
    room_id: int | None = None  # None = 호텔 전체 휴무
    closed_date: date
    # 분류를 안 보내면 ETC(기타)로 보고 reason(상세)이 필수. 기타가 아니면 상세는 선택.
    reason_code: ReasonCode | None = None
    reason: str | None = Field(default=None, max_length=190)  # #66-3: 표시용 "점검 · " + 상세가 200자 안


class ClosedDateRangeCreate(CamelModel):
    """Step 2 3A 휴무 기간 지정: start ~ end(포함), 최대 31일."""
    room_id: int | None = None  # None = 호텔 전체 휴무, 있으면 그 방 기간 판매 중지
    start_date: date
    end_date: date
    reason_code: ReasonCode | None = None
    reason: str | None = Field(default=None, max_length=190)  # #66-3: 표시용 "점검 · " + 상세가 200자 안


class ClosedDateOut(CamelModel):
    closed_date_id: int
    room_id: int | None
    room_name: str | None = None  # 호텔 전체 휴무면 None
    closed_date: date
    reason: str | None  # 화면 표시용 "점검 · 보일러"
    closure_id: int | None = None


class ClosureOut(CamelModel):
    """휴무 묶음(3-A1): 기간은 남은 날짜 행의 처음 · 끝."""
    closure_id: int
    room_id: int | None
    room_name: str | None = None
    reason_code: ReasonCode
    reason: str | None  # 상세 사유
    start_date: date
    end_date: date
    days: int  # 남은 날짜 수 (하루만 해제했으면 기간보다 적다)
    status: ClosureStatus
    created_by: int | None
