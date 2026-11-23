"""객실 추천 (ROOM-001).

추천 점수 = 조회수 × 0.3 + 최근 30일 예약 수 × 0.7  (가중치는 팀 협의 후 조정)
"""
from datetime import date, timedelta

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models import ClosedDate, Reservation, Room
from app.models.reservation import LIVE_STATUSES
from app.schemas.room import RecommendRoomOut, RoomSort

VIEW_WEIGHT = 0.3
RESERVATION_WEIGHT = 0.7


def available_room_filter(check_in: date, check_out: date):
    """해당 기간에 예약(대기·승인)이나 휴무일이 겹치지 않는 객실 조건."""
    overlapping_reservation = exists().where(
        Reservation.room_id == Room.room_id,
        Reservation.status.in_(LIVE_STATUSES),
        Reservation.check_in_date < check_out,
        Reservation.check_out_date > check_in,
    )
    closed = exists().where(
        or_(ClosedDate.room_id == Room.room_id, ClosedDate.room_id.is_(None)),
        ClosedDate.closed_date >= check_in,
        ClosedDate.closed_date < check_out,
    )
    return and_(~overlapping_reservation, ~closed)


def recommend_rooms(
    db: Session,
    *,
    check_in: date | None,
    check_out: date | None,
    guests: int | None,
    sort: RoomSort,
    page: int,
    size: int,
) -> tuple[list[RecommendRoomOut], int]:
    since = date.today() - timedelta(days=30)
    recent = (
        select(Reservation.room_id, func.count().label("cnt"))
        .where(Reservation.status.in_(LIVE_STATUSES), Reservation.created_at >= since)
        .group_by(Reservation.room_id)
        .subquery()
    )
    recent_cnt = func.coalesce(recent.c.cnt, 0)
    score = Room.view_count * VIEW_WEIGHT + recent_cnt * RESERVATION_WEIGHT

    conditions = [Room.is_active == "Y"]
    if guests:
        conditions.append(Room.max_guest >= guests)
    if check_in and check_out:
        conditions.append(available_room_filter(check_in, check_out))

    base = select(Room, recent_cnt.label("recent"), score.label("score")).outerjoin(
        recent, recent.c.room_id == Room.room_id
    ).where(*conditions)

    order = {
        "recommend": [score.desc(), Room.room_id],
        "popular": [recent_cnt.desc(), Room.room_id],
        "price": [Room.price.asc(), Room.room_id],
    }[sort]

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(*order).offset((page - 1) * size).limit(size)).all()

    items = []
    for idx, (room, recent_value, score_value) in enumerate(rows):
        out = RecommendRoomOut.model_validate(room)
        out.recent_reservations = recent_value
        out.score = round(float(score_value), 2)
        out.is_recommended = sort == "recommend" and page == 1 and idx == 0
        items.append(out)
    return items, total
