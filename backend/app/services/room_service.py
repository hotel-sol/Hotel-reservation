"""객실 추천 (ROOM-001).

추천 점수(0~100) = (조회수 / 최대 조회수) × 40 + (최근 30일 승인 예약 수 / 최대 최근 승인 예약 수) × 60
(11-24 팀 결정: 조회 40 · 예약 60, 예약은 관리자가 승인한 것만)
- 화면설계서의 '조회수 × 0.3 + 예약 수 × 0.7'을 그대로 곱하면 조회수(수백)가 예약 수(몇 건)를 압도해서
  조회수만으로 순위가 정해진다. 그래서 각각 최대값 대비 비율로 맞춘 뒤 가중치를 곱한다.
- 최대값은 '판매 중인 객실 전체' 기준이라 검색 조건이 바뀌어도 같은 방의 점수는 같다.
- 가중치는 VIEW_WEIGHT · RESERVATION_WEIGHT 두 상수만 바꾸면 된다.

예약 수는 승인(APPROVED) 예약만 센다. 대기는 취소될 수 있어서 빼고, 취소도 세지 않는다.
(빈방 검색은 다르다: 대기 예약도 방을 잡고 있으므로 available_room_filter 는 대기 + 승인을 본다)
- 추천순: 점수 높은 순 / 인기순: 전체 승인 예약 수 많은 순 / 낮은 가격순: 1박 요금 오름차순

뱃지(하나만, 우선순위 BEST > HOT > NEW). 검색 조건 · 정렬과 상관없이 판매 중인 객실 전체에서 정한다.
- BEST: 추천 점수 1~3위(점수 0 초과)  → 화면의 "★ 추천"
- HOT : 최근 7일 승인 예약 수 1~3위(1건 이상)
- NEW : 등록 14일 이내
"""
from datetime import date, timedelta

from sqlalchemy import Numeric, and_, case, cast, exists, func, literal, or_, select
from sqlalchemy.orm import Session

from app.core.dates import today_kst
from app.models import AttachFile, ClosedDate, Reservation, Room
from app.models.reservation import APPROVED, LIVE_STATUSES
from app.schemas.room import RecommendRoomOut, RoomDetailOut, RoomSort

VIEW_WEIGHT = 0.4
RESERVATION_WEIGHT = 0.6
RECENT_DAYS = 30
HOT_DAYS = 7
NEW_DAYS = 14
BADGE_TOP = 3


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


def _scoring(db: Session):
    """예약 수 · 추천 점수 식. 추천 목록과 객실 상세(뱃지)가 같이 쓴다."""
    today = today_kst()
    since = today - timedelta(days=RECENT_DAYS)
    hot_since = today - timedelta(days=HOT_DAYS)
    counts = (
        select(
            Reservation.room_id,
            func.count().label("total"),
            func.sum(case((Reservation.created_at >= since, 1), else_=0)).label("recent"),
            func.sum(case((Reservation.created_at >= hot_since, 1), else_=0)).label("week"),
        )
        .where(Reservation.status == APPROVED)
        .group_by(Reservation.room_id)
        .subquery()
    )
    recent_cnt = func.coalesce(counts.c.recent, 0)
    total_cnt = func.coalesce(counts.c.total, 0)
    week_cnt = func.coalesce(counts.c.week, 0)
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
    return with_counts, recent_cnt, total_cnt, week_cnt, score


def _badges(db: Session, with_counts, recent_cnt, week_cnt, score) -> dict[int, str]:
    """판매 중인 객실 전체에서 뱃지를 정한다(검색 조건 · 페이지와 무관). 뱃지 없는 방은 빠진다."""
    ranked = db.execute(
        with_counts.with_only_columns(Room.room_id, score.label("score"), week_cnt.label("week"), Room.created_at)
        .where(Room.is_active == "Y")
        .order_by(score.desc(), recent_cnt.desc(), Room.room_id)
    ).all()
    best = {r.room_id for r in [r for r in ranked if r.score > 0][:BADGE_TOP]}
    hot = {r.room_id for r in sorted((r for r in ranked if r.week > 0), key=lambda r: (-r.week, r.room_id))[:BADGE_TOP]}
    new_since = today_kst() - timedelta(days=NEW_DAYS)
    badges = {}
    for r in ranked:
        if r.room_id in best:
            badges[r.room_id] = "BEST"
        elif r.room_id in hot:
            badges[r.room_id] = "HOT"
        elif r.created_at and r.created_at.date() >= new_since:
            badges[r.room_id] = "NEW"
    return badges


def room_detail(db: Session, room: Room) -> RoomDetailOut:
    """객실 상세: 객실 정보 + 사진 전부 + 뱃지 + 예약 수."""
    with_counts, recent_cnt, total_cnt, week_cnt, score = _scoring(db)
    row = db.execute(
        with_counts.with_only_columns(recent_cnt, total_cnt, score).where(Room.room_id == room.room_id)
    ).one()
    out = RoomDetailOut.model_validate(room)
    out.recent_reservations, out.total_reservations, out.score = int(row[0]), int(row[1]), round(float(row[2]), 2)
    out.badge = _badges(db, with_counts, recent_cnt, week_cnt, score).get(room.room_id)
    out.is_recommended = out.badge == "BEST"
    out.photos = list(db.scalars(
        select(AttachFile.saved_path)
        .where(AttachFile.target_type == "ROOM", AttachFile.target_id == room.room_id)
        .order_by(AttachFile.file_id)
    ))
    out.thumbnail_url = out.photos[0] if out.photos else None
    return out


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
    with_counts, recent_cnt, total_cnt, week_cnt, score = _scoring(db)
    thumbnail = (
        select(AttachFile.saved_path)
        .where(AttachFile.target_type == "ROOM", AttachFile.target_id == Room.room_id)
        .order_by(AttachFile.file_id)
        .limit(1)
        .scalar_subquery()
    )
    badges = _badges(db, with_counts, recent_cnt, week_cnt, score)

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
    for room, recent_value, total_value, score_value, thumbnail_value in rows:
        out = RecommendRoomOut.model_validate(room)
        out.recent_reservations = int(recent_value)
        out.total_reservations = int(total_value)
        out.score = round(float(score_value), 2)
        out.thumbnail_url = thumbnail_value
        out.badge = badges.get(room.room_id)
        out.is_recommended = out.badge == "BEST"
        items.append(out)
    return items, total
