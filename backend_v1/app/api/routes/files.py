"""첨부파일 (공통) — 객실 사진 업로드"""
from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import AdminMember
from app.core.exceptions import fail

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", status_code=201)
async def upload_file(
    admin: AdminMember,
    target_type: str = Form(..., alias="targetType"),
    target_id: int = Form(..., alias="targetId"),
    file: UploadFile = File(...),
):
    # TODO(ADM-001): jpg·png 만, 객실당 최대 5장. settings.upload_dir 에 저장 후 attach_file INSERT
    fail(501, "NOT_IMPLEMENTED", "준비 중입니다.")
