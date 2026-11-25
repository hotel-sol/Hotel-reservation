"""FastAPI 진입점 — 실행: uv run fastapi dev app/main.py  (backend 폴더에서)"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import DataError

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,  # 세션 쿠키
    allow_methods=["*"],
    allow_headers=["*"],
)

NUMERIC_OUT_OF_RANGE = "22003"  # PostgreSQL: 숫자가 칸 범위를 넘음 (예: BIGINT 보다 큰 번호)


@app.exception_handler(DataError)
async def number_out_of_range(request: Request, exc: DataError):
    """#76 공통: 주소 · 폼에 DB 숫자 범위를 넘는 번호(예: /api/rooms/99999999999999999999)가 오면
    그런 번호의 행은 있을 수 없으므로 500 대신 404. 파트마다 고치지 않고 여기 한 곳에서 처리한다.
    다른 DataError 는 그대로 500 (숨기지 않음)."""
    if getattr(exc.orig, "sqlstate", None) != NUMERIC_OUT_OF_RANGE:
        raise exc
    return JSONResponse(status_code=404, content={"detail": {"code": "NOT_FOUND", "message": "찾을 수 없습니다."}})


# 모든 API 는 /api 아래 (프론트 Next.js 가 /api/* 를 이 서버로 프록시)
app.include_router(api_router, prefix="/api")

# 올린 사진(attach_file.saved_path = "uploads/...")을 /uploads/... 주소로 내준다.
# 화면(Next.js)은 next.config.ts 의 rewrites 로 /uploads/* 를 이 서버로 넘긴다.
_upload_dir = Path(settings.upload_dir)
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_upload_dir), name="uploads")
