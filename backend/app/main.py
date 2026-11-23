"""FastAPI 진입점 — 실행: uv run fastapi dev app/main.py  (backend 폴더에서)"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

# 모든 API 는 /api 아래 (프론트 Next.js 가 /api/* 를 이 서버로 프록시)
app.include_router(api_router, prefix="/api")

# 올린 사진(attach_file.saved_path = "uploads/...")을 /uploads/... 주소로 내준다.
# 화면(Next.js)은 next.config.ts 의 rewrites 로 /uploads/* 를 이 서버로 넘긴다.
_upload_dir = Path(settings.upload_dir)
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_upload_dir), name="uploads")
