"""첨부파일 (공통) — 객실 사진 업로드 · 목록 · 삭제 (ADM-001)

규칙
- 관리자만 (AdminMember)
- 지금은 객실 사진만: targetType = "ROOM", targetId = 객실 번호
- jpg · png 만 (확장자와 파일 앞부분 모양을 둘 다 확인)
- 객실당 최대 5장, 한 장 최대 5MB
- 파일은 <UPLOAD_DIR>/rooms/<무작위이름>.<확장자> 에 저장,
  DB(attach_file.saved_path)에는 "uploads/rooms/<무작위이름>.<확장자>" 로 기록
  → main.py 가 /uploads 를 정적 파일로 내주고, Next.js 가 /uploads/* 를 백엔드로 넘겨서 화면에 보인다.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy import func, select

from app.api.deps import DB, AdminMember
from app.core.config import get_settings
from app.core.exceptions import fail
from app.models import AttachFile, Room
from app.schemas.common import CamelModel

router = APIRouter(prefix="/files", tags=["files"])

MAX_FILES_PER_ROOM = 5
MAX_BYTES = 5 * 1024 * 1024
# 확장자 → 파일 맨 앞 바이트(진짜 그 형식인지 확인용)
ALLOWED = {
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG\r\n\x1a\n",
}


class FileOut(CamelModel):
    file_id: int
    target_type: str
    target_id: int
    original_name: str
    saved_path: str  # 화면은 앞에 "/" 를 붙여 그대로 <img src> 로 쓴다 (lib/format.ts fileUrl)
    file_size: int


def room_dir() -> Path:
    path = Path(get_settings().upload_dir) / "rooms"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_room(db, target_type: str, target_id: int) -> None:
    if target_type != "ROOM":
        fail(400, "UNSUPPORTED_TARGET", "지금은 객실 사진(ROOM)만 올릴 수 있습니다.")
    if not db.get(Room, target_id):
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")


@router.post("", response_model=FileOut, status_code=201)
async def upload_file(
    admin: AdminMember,
    db: DB,
    target_type: str = Form(..., alias="targetType"),
    target_id: int = Form(..., alias="targetId"),
    file: UploadFile = File(...),
):
    ensure_room(db, target_type, target_id)

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        fail(400, "INVALID_FILE_TYPE", "jpg 또는 png 파일만 올릴 수 있습니다.")

    data = await file.read(MAX_BYTES + 1)
    if not data:
        fail(400, "EMPTY_FILE", "빈 파일입니다.")
    if len(data) > MAX_BYTES:
        fail(400, "FILE_TOO_LARGE", "사진은 한 장에 5MB까지 올릴 수 있습니다.")
    if not data.startswith(ALLOWED[ext]):
        fail(400, "INVALID_FILE_TYPE", "jpg 또는 png 파일만 올릴 수 있습니다.")

    count = db.scalar(
        select(func.count()).select_from(AttachFile)
        .where(AttachFile.target_type == target_type, AttachFile.target_id == target_id)
    ) or 0
    if count >= MAX_FILES_PER_ROOM:
        fail(409, "TOO_MANY_FILES", f"객실 사진은 최대 {MAX_FILES_PER_ROOM}장까지 올릴 수 있습니다.")

    name = f"{uuid.uuid4().hex}{'.jpg' if ext == '.jpeg' else ext}"
    saved = room_dir() / name
    saved.write_bytes(data)

    row = AttachFile(
        target_type=target_type,
        target_id=target_id,
        original_name=(file.filename or name)[:255],
        saved_path=f"uploads/rooms/{name}",
        file_size=len(data),
    )
    try:
        db.add(row)
        db.commit()
    except Exception:
        # DB 기록이 실패하면 방금 저장한 파일도 지운다 (화면에 안 보이는 파일이 디스크에 남지 않게)
        db.rollback()
        saved.unlink(missing_ok=True)
        raise
    db.refresh(row)
    return row


@router.get("", response_model=list[FileOut])
def list_files(
    admin: AdminMember,
    db: DB,
    target_type: str = Query(..., alias="targetType"),
    target_id: int = Query(..., alias="targetId"),
):
    """한 객실의 사진 목록 (올린 순서. 첫 장이 추천 카드의 대표 사진)."""
    return db.scalars(
        select(AttachFile)
        .where(AttachFile.target_type == target_type, AttachFile.target_id == target_id)
        .order_by(AttachFile.file_id)
    ).all()


@router.delete("/{file_id}", status_code=204)
def delete_file(file_id: int, admin: AdminMember, db: DB):
    row = db.get(AttachFile, file_id) or fail(404, "FILE_NOT_FOUND", "파일을 찾을 수 없습니다.")
    (room_dir() / Path(row.saved_path).name).unlink(missing_ok=True)
    db.delete(row)
    db.commit()
