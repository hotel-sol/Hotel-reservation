"""관리자) 예약 관리 — ADM-003

상태 전이: PENDING → APPROVED/CANCELED, APPROVED → CANCELED, CANCELED → (불가)
체크인이 지난 예약은 취소 불가(오늘은 한국 시간 기준). 변경 시 updated_at 기록.
취소하면 canceled_at(취소 시각) · canceled_by(취소한 관리자 member_id)도 남긴다 (4-A4).

GET   /admin/reservations?status=&from=&to=&keyword=&page=&size=   목록 (① 탭 · ② 검색)
GET   /admin/reservations/counts?from=&to=&keyword=                 상태별 건수 (① 탭 옆 숫자)
PATCH /admin/reservations/{id}/approve · /cancel                    승인 · 취소 (③)
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select

from app.api.deps import DB, AdminMember, require_admin
from app.core.dates import today_kst
from app.core.exceptions import fail
from app.models import Member, Reservation, Room
from app.models.reservation import APPROVED, CANCELED, PENDING
from app.schemas.common import Page
from app.schemas.reservation import ReservationOut

router = APIRouter(
    prefix="/admin/reservations", tags=["admin: reservations"], dependencies=[Depends(require_admin)]
)


STATUS_LABEL = {PENDING: "승인 대기", APPROVED: "승인", CANCELED: "취소"}

FromQuery = Query(None, alias="from")
ToQuery = Query(None, alias="to")


def search_conditions(from_date: date | None, to_date: date | None, keyword: str | None) -> list:
    """② 검색 조건: 체크인 기간, 예약자명(부분 일치) 또는 예약 번호. 목록과 탭 건수가 같이 쓴다."""
    conds = []
    if from_date:
        conds.append(Reservation.check_in_date >= from_date)
    if to_date:
        conds.append(Reservation.check_in_date <= to_date)
    keyword = (keyword or "").strip()
    if keyword:
        cond = Member.name.icontains(keyword)
        if keyword.isdigit():
            cond = or_(cond, Reservation.reservation_id == int(keyword))
        conds.append(cond)
    return conds


@router.get("", response_model=Page[ReservationOut])
def list_reservations(
    db: DB,
    # 생략하면 전체. 화면 기본 탭(승인 대기)은 프론트가 status=PENDING 으로 보낸다.
    status: str | None = Query(None, pattern="^(PENDING|APPROVED|CANCELED)$"),
    from_date: date | None = FromQuery,
    to_date: date | None = ToQuery,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    q = (
        select(Reservation, Room.room_name, Member.name)
        .join(Room, Room.room_id == Reservation.room_id)
        .join(Member, Member.member_id == Reservation.member_id)
        .where(*search_conditions(from_date, to_date, keyword))
    )
    if status:
        q = q.where(Reservation.status == status)

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.execute(q.order_by(Reservation.reservation_id.desc()).offset((page - 1) * size).limit(size)).all()
    items = []
    for r, room_name, member_name in rows:
        out = ReservationOut.model_validate(r)
        out.room_name, out.member_name = room_name, member_name
        items.append(out)
    return Page(items=items, total=total, page=page, size=size)


@router.get("/counts", response_model=dict[str, int])
def status_counts(
    db: DB, from_date: date | None = FromQuery, to_date: date | None = ToQuery, keyword: str | None = None
):
    """상태별 건수 {"ALL": 15, "PENDING": 11, "APPROVED": 3, "CANCELED": 1}. 검색 조건은 목록과 같다."""
    rows = db.execute(
        select(Reservation.status, func.count())
        .join(Member, Member.member_id == Reservation.member_id)
        .where(*search_conditions(from_date, to_date, keyword))
        .group_by(Reservation.status)
    ).all()
    counts = {PENDING: 0, APPROVED: 0, CANCELED: 0} | {status: n for status, n in rows}
    return {"ALL": sum(counts.values()), **counts}


def _change_status(db, reservation_id: int, to: str, admin: Member) -> Reservation:
    r = db.get(Reservation, reservation_id) or fail(404, "RESERVATION_NOT_FOUND", "예약을 찾을 수 없습니다.")
    allowed = {PENDING: {APPROVED, CANCELED}, APPROVED: {CANCELED}, CANCELED: set()}
    if to not in allowed[r.status]:
        fail(409, "INVALID_STATUS", f"이미 {STATUS_LABEL[r.status]} 상태인 예약이라 {STATUS_LABEL[to]}할 수 없습니다.")
    if to == CANCELED and r.check_in_date < today_kst():
        fail(409, "PAST_CHECK_IN", "체크인이 지난 예약은 취소할 수 없습니다.")
    r.status = to
    # created_at 과 같은 DB 시계(now())로 남긴다. 서버 PC 시간대(datetime.now())와 섞이지 않게
    r.updated_at = func.now()
    if to == CANCELED:
        r.canceled_at = func.now()
        r.canceled_by = admin.member_id
    db.commit()
    db.refresh(r)
    return r


@router.patch("/{reservation_id}/approve", response_model=ReservationOut)
def approve(reservation_id: int, db: DB, admin: AdminMember):
    return _change_status(db, reservation_id, APPROVED, admin)


@router.patch("/{reservation_id}/cancel", response_model=ReservationOut)
def cancel(reservation_id: int, db: DB, admin: AdminMember):
    return _change_status(db, reservation_id, CANCELED, admin)
