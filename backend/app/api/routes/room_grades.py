"""객실 등급 목록 (2-A1) — 관리 화면 등급 고르기 · 1번 등급 필터(1-B1)용. 읽기만, 로그인 없이."""
from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DB
from app.models import RoomGrade
from app.schemas.room import RoomGradeOut

router = APIRouter(prefix="/room-grades", tags=["room-grades"])


@router.get("", response_model=list[RoomGradeOut])
def list_grades(db: DB):
    return db.scalars(select(RoomGrade).order_by(RoomGrade.sort_order, RoomGrade.grade_id)).all()
