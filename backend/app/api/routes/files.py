"""첨부파일 (공통) — 객실 사진 업로드 · 목록 · 삭제 (ADM-001)

규칙
- 관리자만 (AdminMember)
- 지금은 객실 사진만: targetType = "ROOM", targetId = 객실 번호
- jpg · png 만 (확장자와 파일 앞부분 모양을 둘 다 확인)
- 객실당 최대 5장, 한 장 최대 5MB. 동시에 올려도 5장을 넘지 않게 객실 행을 잠그고 센다 (#69)
- 파일 저장은 services/photo_storage.py (2-A2):
  .env 에 Supabase Storage 설정이 있으면 공용 버킷에 올리고 saved_path = 공개 주소(https://...)
  없으면 <UPLOAD_DIR>/rooms/ 에 저장하고 saved_path = "uploads/rooms/<무작위이름>.<확장자>"
  → 화면(lib/format.ts fileUrl)은 https 주소는 그대로, 그 밖은 앞에 "/" 를 붙여 <img src> 로 쓴다.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy import func, select

from app.api.deps import DB, AdminMember
from app.core.exceptions import fail
from app.models import AttachFile, Room
from app.schemas.common import CamelModel
from app.services import photo_storage

router = APIRouter(prefix="/files", tags=["files"])

MAX_FILES_PER_ROOM = 5
MAX_BYTES = 5 * 1024 * 1024
# 확장자 → 파일 맨 앞 바이트(진짜 그 형식인지 확인용)
ALLOWED = {
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG\r\n\x1a\n",
}
CONTENT_TYPES = {".jpg": "image/jpeg", ".png": "image/png"}


class FileOut(CamelModel):
    file_id: int
    target_type: str
    target_id: int
    original_name: str
    saved_path: str  # Storage 공개 주소(https://...) 또는 "uploads/rooms/..." (lib/format.ts fileUrl 로 <img src>)
    file_size: int


def lock_room(db, target_type: str, target_id: int) -> None:
    """객실이 있는지 확인하면서 그 행을 잠근다(SELECT … FOR UPDATE). 저장 · commit 이 끝날 때까지
    같은 객실의 다른 업로드는 기다린다 → 장수 세기와 저장 사이에 끼어들 수 없다 (#69 사진 장수 경합)."""
    if target_type != "ROOM":
        fail(400, "UNSUPPORTED_TARGET", "지금은 객실 사진(ROOM)만 올릴 수 있습니다.")
    if db.scalar(select(Room.room_id).where(Room.room_id == target_id).with_for_update()) is None:
        fail(404, "ROOM_NOT_FOUND", "객실을 찾을 수 없습니다.")


@router.post("", response_model=FileOut, status_code=201)
async def upload_file(
    admin: AdminMember,
    db: DB,
    target_type: str = Form(..., alias="targetType"),
    target_id: int = Form(..., alias="targetId"),
    file: UploadFile = File(...),
):
    if target_type != "ROOM":
        fail(400, "UNSUPPORTED_TARGET", "지금은 객실 사진(ROOM)만 올릴 수 있습니다.")

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

    lock_room(db, target_type, target_id)  # 여기서부터 commit 까지 이 객실 업로드는 한 번에 하나
    count = db.scalar(
        select(func.count()).select_from(AttachFile)
        .where(AttachFile.target_type == target_type, AttachFile.target_id == target_id)
    ) or 0
    if count >= MAX_FILES_PER_ROOM:
        fail(409, "TOO_MANY_FILES", f"객실 사진은 최대 {MAX_FILES_PER_ROOM}장까지 올릴 수 있습니다.")

    ext = ".jpg" if ext == ".jpeg" else ext
    name = f"{uuid.uuid4().hex}{ext}"
    try:
        saved_path = photo_storage.save(name, data, CONTENT_TYPES[ext])
    except Exception:
        db.rollback()  # 객실 잠금 풀기
        raise

    row = AttachFile(
        target_type=target_type,
        target_id=target_id,
        original_name=(file.filename or name)[:255],
        saved_path=saved_path,
        file_size=len(data),
    )
    try:
        db.add(row)
        db.commit()
    except Exception:
        # DB 기록이 실패하면 방금 저장한 파일도 지운다 (화면에 안 보이는 파일이 남지 않게)
        db.rollback()
        photo_storage.remove(saved_path)
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
    saved_path = row.saved_path
    # DB 기록을 먼저 지우고, 성공하면 파일을 지운다 (반대 순서면 DB 실패 때 목록엔 있는데 사진이 깨짐)
    db.delete(row)
    db.commit()
    photo_storage.remove(saved_path)
