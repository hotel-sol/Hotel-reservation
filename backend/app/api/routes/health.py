from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DB

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/db")
def health_db(db: DB):
    version = db.execute(text("SELECT @@VERSION")).scalar_one()
    return {"status": "ok", "db": version.splitlines()[0]}
