"""관리자) 객실 관리 — ADM-001"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, require_admin
from app.core.dates import today_kst
from app.core.exceptions import fail
from app.models import ClosedDate, Reservation, Room, RoomGrade
from app.models.reservation import LIVE_STATUSES
from app.schemas.common import Page
from app.schemas.room import RoomCreate, RoomOut, RoomStatusUpdate, RoomSummary, RoomUpdate

router = APIRouter(prefix="/admin/rooms", tags=["admin: rooms"], dependencies=[Depends(require_admin)])


def ensure_unique_name(db, name: str, exclude_id: int | None = None):
    q = select(Room.room_id).where(Room.room_name == name)
    if exclude_id:
        q = q.where(Room.room_id != exclude_id)
    if db.scalar(q):
        fail(409, "DUPLICATE_ROOM_NAME", "이미 있는 객실 이름입니다.")


def commit_room(db, name: str, exclude_id: int | None = None) -> None:
    """#76-4: 같은 이름을 거의 동시에 두 번 저장하면 둘 다 중복 확인을 통과하고, 늦은 쪽은 DB UNIQUE 에 걸린다.
    그 오류를 500 대신 409 DUPLICATE_ROOM_NAME 으로 돌려준다 (다른 이유의 DB 오류는 그대로)."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        ensure_unique_name(db, name, exclude_id)
        raise


def room_values(db, body: RoomCreate) -> dict:
    """저장할 값. 등급을 골랐으면 객실 종류(room_type)를 등급 이름으로 맞춘다 (1 · 4 · 5번은 room_type 글자를 그대로 읽음)."""
    values = body.model_dump()
    if body.grade_id is not None:
        grade = db.get(RoomGrade, body.grade_id) or fail(400, "GRADE_NOT_FOUND", "없는 객실 등급입니다.")
        values["room_type"] = grade.grade_name
    return values


@router.get("", response_model=Page[RoomOut])
def list_rooms(
    db: DB,
    keyword: str | None = None,
    is_active: str | None = Query(None, alias="isActive", pattern="^[YN]$"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    q = select(Room)
    if keyword:
        q = q.where(Room.room_name.icontains(keyword))
    if is_active:
        q = q.where(Room.is_active == is_active)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = db.scalars(q.order_by(Room.room_id.desc()).offset((page - 1) * size).limit(size)).all()
    return Page(items=items, total=total, page=page, size=size)


@router.get("/summary", response_model=RoomSummary)
def room_summary(db: DB):
    """목록 위 요약 카드 (2A). 오늘 = today_kst(). 휴무는 closed_date (room_id NULL = 호텔 전체 → 사용 중 객실 전부)."""
    today = today_kst()
    rooms = db.execute(select(Room.room_id, Room.is_active)).all()
    active = {r.room_id for r in rooms if r.is_active == "Y"}

    closures = db.execute(
        select(ClosedDate.room_id, ClosedDate.closed_date).where(ClosedDate.closed_date >= today)
    ).all()

    def closed_ids(match) -> set[int]:
        ids: set[int] = set()
        for c in closures:
            if match(c.closed_date):
                ids |= active if c.room_id is None else ({c.room_id} & active)
        return ids

    closed_today = closed_ids(lambda d: d == today)
    closed_soon = closed_ids(lambda d: d > today) - closed_today
    return RoomSummary(
        total=len(rooms),
        on_sale=len(active - closed_today),
        closed_today=len(closed_today),
        closed_soon=len(closed_soon),
        inactive=len(rooms) - len(active),
        closed_today_room_ids=sorted(closed_today),
        closed_soon_room_ids=sorted(closed_soon),
    )


def future_reservation_count(db, room_id: int) -> int:
    """취소되지 않은 예약 중 체크아웃이 오늘 이후인 예약 수 (API 명세서 v1.3 FUTURE_RESERVATION_EXISTS 규칙)."""
    return db.scalar(
        select(func.count()).select_from(Reservation).where(
            Reservation.room_id == room_id,
            Reservation.status.in_(LIVE_STATUSES),
            Reservation.check_out_date > today_kst(),
        )
    ) or 0


@router.post("", response_model=RoomOut, status_code=201)
def create_room(body: RoomCreate, db: DB):
    ensure_unique_name(db, body.room_name)
    room = Room(**room_values(db, body))
    db.add(room)
    commit_room(db, body.room_name)
    db.refresh(room)
    return room


@router.put("/{room_id}", response_model=RoomOut)
def update_room(room_id: int, body: RoomUpdate, db: DB):
    room = db.get(Room, room_id) or fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    ensure_unique_name(db, body.room_name, exclude_id=room_id)
    values = room_values(db, body)
    # 2A: 앞으로 묵을 예약이 있으면 종류(등급) · 인원 · 요금은 못 바꾼다 (이미 받은 예약과 어긋나지 않게).
    # 이름 · 설명 · 전망 · 침대는 가능 (전망을 바꿔도 요금을 안 바꾸면 예약 금액은 그대로)
    changed = (
        values["room_type"] != room.room_type
        or values["grade_id"] != room.grade_id
        or body.max_guest != room.max_guest
        or body.price != room.price
    )
    if changed and (n := future_reservation_count(db, room_id)):
        fail(
            409,
            "FUTURE_RESERVATION_EXISTS",
            f"앞으로 묵을 예약이 {n}건 있어 객실 종류 · 인원 · 요금을 바꿀 수 없습니다. (이름 · 설명은 바꿀 수 있습니다)",
        )
    for k, v in values.items():
        setattr(room, k, v)
    commit_room(db, body.room_name, exclude_id=room_id)
    return room


@router.patch("/{room_id}/status", response_model=RoomOut)
def change_status(room_id: int, body: RoomStatusUpdate, db: DB):
    # 객실 행을 잠그고 확인 → 확인과 저장 사이에 그 방 예약이 새로 들어오지 못한다 (예약도 객실 행을 잠금, #79)
    room = db.get(Room, room_id, with_for_update=True) or fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    # #76-3 (팀 결정 ⓐ): 앞으로 묵을 예약이 있으면 비활성화도 막는다 — 숨긴 방에 손님 예약만 살아 있지 않게
    if body.is_active == "N" and room.is_active == "Y" and (n := future_reservation_count(db, room_id)):
        fail(
            409,
            "FUTURE_RESERVATION_EXISTS",
            f"앞으로 묵을 예약이 {n}건 있어 비활성화할 수 없습니다. 예약 관리에서 예약을 먼저 취소해 주세요.",
        )
    room.is_active = body.is_active  # 삭제 없음: 비활성화만
    db.commit()
    return room
