"""DB 연결 (SQLAlchemy 2.0 + Supabase PostgreSQL, 드라이버 psycopg)."""
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# 팀 5명이 Supabase 무료 플랜 하나를 같이 써서 동시 연결 수가 모자라지 않게 풀을 작게 둔다.
engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True, pool_size=2, max_overflow=3)


@event.listens_for(engine, "connect")
def use_schema(dbapi_conn, _record):
    """연결마다 우리 테이블이 있는 스키마를 먼저 보게 한다 (앱 hotel, 테스트 hotel_test)."""
    with dbapi_conn.cursor() as cur:
        cur.execute(f'SET search_path TO "{settings.db_schema}", public')
    dbapi_conn.commit()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
