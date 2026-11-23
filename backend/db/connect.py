"""공용 DB 연결. 모든 파트가 이걸 쓴다.

    from db.connect import connect, get_db
    def my_api(db=Depends(get_db)): ...      # API: 요청마다 연결을 열고 끝나면 닫는다
    conn = connect()                          # 스크립트 · 테스트

접속값은 환경변수, 없으면 backend/.env (커밋 금지, .env.example을 복사해서 만든다).
"""
import os
from pathlib import Path

import pymysql

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env(path: Path = ENV_FILE) -> None:
    """KEY=VALUE 줄만 읽는다. 이미 있는 환경변수가 이긴다."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env()


def connect(database: str | None = None):
    """database="" 이면 DB를 고르지 않고 접속한다(DB 만들기용)."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=database if database is not None else os.getenv("DB_NAME", "hotel"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
