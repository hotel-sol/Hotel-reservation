"""객실 추천 (ROOM-001).

추천 점수(0~100) = (조회수 / 최대 조회수) × 30 + (최근 30일 예약 수 / 최대 최근 예약 수) × 70
- 화면설계서의 '조회수 × 0.3 + 예약 수 × 0.7'을 그대로 곱하면 조회수(수백)가 예약 수(몇 건)를 압도해서
  조회수만으로 순위가 정해진다. 그래서 각각 최대값 대비 비율로 맞춘 뒤 가중치를 곱한다.
- 최대값은 '판매 중인 객실 전체' 기준이라 검색 조건이 바뀌어도 같은 방의 점수는 같다.
- 가중치는 VIEW_WEIGHT · RESERVATION_WEIGHT 두 상수만 바꾸면 된다(팀 협의 대상).

예약 수는 살아 있는 예약(대기 + 승인)만 센다. 취소는 세지 않는다.
- 추천순: 점수 높은 순. 1등(1페이지 첫 번째, 점수 0 초과)에만 "추천"
- 인기순: 전체 예약 수 많은 순
- 낮은 가격순: 1박 요금 오름차순
"""
from datetime import date, timedelta

from sqlalchemy import Numeric, and_, case, cast, exists, func, literal, or_, select
from sqlalchemy.orm import Session

from app.core.dates import today_kst
from app.models import AttachFile, ClosedDate, Reservation, Room
from app.models.reservation import LIVE_STATUSES
from app.schemas.room import RecommendRoomOut, RoomSort

VIEW_WEIGHT = 0.3
RESERVATION_WEIGHT = 0.7
RECENT_DAYS = 30


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


def _ratio(value, max_value: int):
    """value / 최대값. 최대값이 0이면(아무도 없으면) 0."""
    return value * (1.0 / max_value) if max_value else literal(0)


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
    since = today_kst() - timedelta(days=RECENT_DAYS)
    counts = (
        select(
            Reservation.room_id,
            func.count().label("total"),
            func.sum(case((Reservation.created_at >= since, 1), else_=0)).label("recent"),
        )
        .where(Reservation.status.in_(LIVE_STATUSES))
        .group_by(Reservation.room_id)
        .subquery()
    )
    recent_cnt = func.coalesce(counts.c.recent, 0)
    total_cnt = func.coalesce(counts.c.total, 0)
    with_counts = select(Room).outerjoin(counts, counts.c.room_id == Room.room_id)

    # 비율의 기준: 판매 중인 객실 전체의 최대 조회수 · 최대 최근 예약 수
    max_view = db.scalar(select(func.max(Room.view_count)).where(Room.is_active == "Y")) or 0
    max_recent = db.scalar(
        with_counts.with_only_columns(func.max(recent_cnt)).where(Room.is_active == "Y")
    ) or 0
    # PostgreSQL 의 round(값, 자리수)는 numeric 만 받는다
    score = func.round(
        cast(
            _ratio(Room.view_count, int(max_view)) * (VIEW_WEIGHT * 100)
            + _ratio(recent_cnt, int(max_recent)) * (RESERVATION_WEIGHT * 100),
            Numeric,
        ),
        2,
    )
    thumbnail = (
        select(AttachFile.saved_path)
        .where(AttachFile.target_type == "ROOM", AttachFile.target_id == Room.room_id)
        .order_by(AttachFile.file_id)
        .limit(1)
        .scalar_subquery()
    )

    conditions = [Room.is_active == "Y"]
    if guests:
        conditions.append(Room.max_guest >= guests)
    if check_in and check_out:
        conditions.append(available_room_filter(check_in, check_out))

    base = with_counts.add_columns(
        recent_cnt.label("recent"), total_cnt.label("total"), score.label("score"), thumbnail.label("thumbnail")
    ).where(*conditions)
    order = {
        "recommend": [score.desc(), recent_cnt.desc(), Room.room_id],
        "popular": [total_cnt.desc(), score.desc(), Room.room_id],
        "price": [Room.price.asc(), score.desc(), Room.room_id],
    }[sort]

    total = db.scalar(select(func.count()).select_from(select(Room.room_id).where(*conditions).subquery())) or 0
    rows = db.execute(base.order_by(*order).offset((page - 1) * size).limit(size)).all()

    items = []
    for idx, (room, recent_value, total_value, score_value, thumbnail_value) in enumerate(rows):
        out = RecommendRoomOut.model_validate(room)
        out.recent_reservations = int(recent_value)
        out.total_reservations = int(total_value)
        out.score = round(float(score_value), 2)
        out.thumbnail_url = thumbnail_value
        out.is_recommended = sort == "recommend" and page == 1 and idx == 0 and out.score > 0
        items.append(out)
    return items, total
