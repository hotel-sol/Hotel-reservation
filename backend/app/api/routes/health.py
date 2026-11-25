from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DB

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/db")
def health_db(db: DB):
    """DB 연결 확인. 로그인 없이 부르는 주소라 DB 종류 · 버전은 알려 주지 않는다 (#70)."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
