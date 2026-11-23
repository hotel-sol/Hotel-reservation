"""관리자) 객실 관리 — ADM-001"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.deps import DB, require_admin
from app.core.exceptions import fail
from app.models import Room
from app.schemas.common import Page
from app.schemas.room import RoomCreate, RoomOut, RoomStatusUpdate, RoomUpdate

router = APIRouter(prefix="/admin/rooms", tags=["admin: rooms"], dependencies=[Depends(require_admin)])


def ensure_unique_name(db, name: str, exclude_id: int | None = None):
    q = select(Room.room_id).where(Room.room_name == name)
    if exclude_id:
        q = q.where(Room.room_id != exclude_id)
    if db.scalar(q):
        fail(409, "DUPLICATE_ROOM_NAME", "이미 있는 객실 이름입니다.")


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


@router.post("", response_model=RoomOut, status_code=201)
def create_room(body: RoomCreate, db: DB):
    ensure_unique_name(db, body.room_name)
    room = Room(**body.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.put("/{room_id}", response_model=RoomOut)
def update_room(room_id: int, body: RoomUpdate, db: DB):
    room = db.get(Room, room_id) or fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    ensure_unique_name(db, body.room_name, exclude_id=room_id)
    for k, v in body.model_dump().items():
        setattr(room, k, v)
    db.commit()
    return room


@router.patch("/{room_id}/status", response_model=RoomOut)
def change_status(room_id: int, body: RoomStatusUpdate, db: DB):
    room = db.get(Room, room_id) or fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")
    room.is_active = body.is_active  # 삭제 없음: 비활성화만
    db.commit()
    return room
