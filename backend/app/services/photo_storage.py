"""객실 사진 파일 저장 (2-A2) — Supabase Storage(공용) 또는 내 컴퓨터(upload_dir).

.env 에 SUPABASE_URL · SUPABASE_SECRET_KEY 가 둘 다 있으면 Storage 버킷에 올리고,
attach_file.saved_path 에 공개 주소(https://<프로젝트>.supabase.co/storage/v1/object/public/<버킷>/...)를 적는다.
없으면 예전처럼 <upload_dir>/rooms/ 에 저장하고 "uploads/rooms/<이름>" 을 적는다 (main.py 가 /uploads 로 내줌).

- Storage 안 경로는 <DB_SCHEMA>/rooms/<무작위이름> — 각자 연습 사진과 공용 hotel 사진이 섞이지 않게
- 시연용 사진(saved_path = "room-photos/...", frontend/public)은 저장 · 삭제하지 않는다
- 추가 설치 없이 파이썬 기본 urllib 로 Storage REST API 를 부른다
"""
import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import fail

log = logging.getLogger(__name__)

LOCAL_PREFIX = "uploads/rooms/"
TIMEOUT_SECONDS = 20


def room_dir() -> Path:
    path = Path(get_settings().upload_dir) / "rooms"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _base() -> str:
    return get_settings().supabase_url.rstrip("/") + "/storage/v1/object"


def public_prefix() -> str:
    """이 버킷 사진의 공개 주소 앞부분. saved_path 가 이것으로 시작하면 Storage 사진."""
    return f"{_base()}/public/{get_settings().storage_bucket}/"


def _call(method: str, url: str, data: bytes, content_type: str) -> None:
    key = get_settings().supabase_secret_key
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": content_type},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS):
        pass


def save(name: str, data: bytes, content_type: str) -> str:
    """사진을 저장하고 attach_file.saved_path 에 적을 값을 돌려준다."""
    s = get_settings()
    if not s.storage_enabled:
        (room_dir() / name).write_bytes(data)
        return LOCAL_PREFIX + name

    path = f"{s.db_schema}/rooms/{name}"
    try:
        _call("POST", f"{_base()}/{s.storage_bucket}/{path}", data, content_type)
    except (urllib.error.URLError, TimeoutError) as e:
        detail = e.read().decode(errors="replace")[:200] if isinstance(e, urllib.error.HTTPError) else str(e)
        log.warning("Storage 업로드 실패: %s", detail)
        fail(502, "STORAGE_FAILED", "사진 저장소에 올리지 못했습니다. 잠시 뒤 다시 시도해 주세요.")
    return public_prefix() + path


def remove(saved_path: str) -> None:
    """저장한 사진 파일을 지운다. 실패해도 오류를 내지 않는다(DB 기록은 이미 정리된 뒤라 화면엔 영향 없음)."""
    try:
        if saved_path.startswith(LOCAL_PREFIX):
            (room_dir() / Path(saved_path).name).unlink(missing_ok=True)
        elif get_settings().storage_enabled and saved_path.startswith(public_prefix()):
            path = saved_path[len(public_prefix()):]
            body = json.dumps({"prefixes": [path]}).encode()
            _call("DELETE", f"{_base()}/{get_settings().storage_bucket}", body, "application/json")
        # 그 밖(시연용 room-photos/ 등)은 지우지 않는다
    except (OSError, urllib.error.URLError) as e:
        log.warning("사진 파일 삭제 실패(%s): %s", saved_path, e)
