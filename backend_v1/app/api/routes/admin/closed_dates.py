"""관리자) 예약 일자(휴무일) 관리 — ADM-002"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.deps import DB, require_admin
from app.core.exceptions import fail
from app.models import ClosedDate
from app.schemas.closed_date import ClosedDateCreate, ClosedDateOut

router = APIRouter(
    prefix="/admin/closed-dates", tags=["admin: closed-dates"], dependencies=[Depends(require_admin)]
)


@router.get("", response_model=list[ClosedDateOut])
def list_closed_dates(
    db: DB,
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    room_id: int | None = Query(None, alias="roomId"),
):
    # TODO(ADM-002): 날짜별 예약 수(대기+승인)도 함께 내려주기
    year, mon = map(int, month.split("-"))
    start = f"{year:04d}-{mon:02d}-01"
    end = f"{year + (mon == 12):04d}-{mon % 12 + 1:02d}-01"
    q = select(ClosedDate).where(ClosedDate.closed_date >= start, ClosedDate.closed_date < end)
    q = q.where(ClosedDate.room_id == room_id) if room_id else q.where(ClosedDate.room_id.is_(None))
    return db.scalars(q.order_by(ClosedDate.closed_date)).all()


@router.post("", response_model=ClosedDateOut, status_code=201)
def create_closed_date(body: ClosedDateCreate, db: DB):
    # TODO(ADM-002): 지난 날짜 · 예약이 있는 날짜 · 중복 지정 차단
    fail(501, "NOT_IMPLEMENTED", "준비 중입니다.")


@router.delete("/{closed_date_id}", status_code=204)
def delete_closed_date(closed_date_id: int, db: DB):
    row = db.get(ClosedDate, closed_date_id) or fail(404, "NOT_FOUND", "휴무일을 찾을 수 없습니다.")
    db.delete(row)
    db.commit()
