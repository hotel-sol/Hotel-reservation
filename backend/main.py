"""태양의 호텔 백엔드 진입점. backend 폴더에서: uvicorn main:app --reload

파트마다 backend/<파트>/<파트>.py 에 router(API)를 만들면 여기서 자동으로 붙는다. 이 파일은 고치지 않아도 된다.
- router: API. 앞에 /api 가 붙는다 (예: /api/admin/closed-dates). Next.js는 /api/... 를 이 서버로 넘긴다.
- pages:  임시 HTML 화면(선택). /api 없이 붙는다. Next.js 화면이 생기면 지운다.
"""
import importlib
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
PARTS = ("member", "room", "roomdate", "reservation", "common")

app = FastAPI(title="태양의 호텔 API")
for part in PARTS:
    module = importlib.import_module(f"{part}.{part}")
    if hasattr(module, "router"):
        app.include_router(module.router, prefix="/api")
    if hasattr(module, "pages"):
        app.include_router(module.pages)

# 임시 HTML 화면용 상단 메뉴와 아직 없는 화면의 뼈대 페이지. Next.js 화면으로 바뀌면 지운다.
app.mount("/layout", StaticFiles(directory=ROOT / "frontend" / "layout"), name="layout")
sys.path.append(str(ROOT / "frontend" / "placeholder"))
from placeholder import add_placeholders  # noqa: E402

add_placeholders(app)
