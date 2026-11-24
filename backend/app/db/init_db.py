"""스키마를 지우고 다시 만든다. backend 폴더에서: uv run python -m app.db.init_db [--no-seed] [--demo] [--reset-shared]

.env의 DB_SCHEMA(각자 hotel_<이름>)를 DROP 후 다시 만들고 팀 DDL(docs/hotel_reservation_ddl.sql), dev_seed.sql 순서로 실행한다.
--demo 를 붙이면 dev_seed.sql 대신 demo_seed.sql(시연용 40실 · 객실 사진)을 넣는다. 공용 hotel 용.
.env에 ADMIN_PASSWORD가 있으면 팀 공용 개발용 관리자 admin01도 만든다.

팀 Supabase 프로젝트 하나를 5명이 같이 쓰므로 실수 방지 장치를 둔다.
- .env에 DB_RESET_ALLOWED=true 가 있어야 실행된다.
- 공용 스키마 hotel(시연 · 통합 확인용)은 --reset-shared 를 직접 붙였을 때만 지운다. 팀에 알리고 실행할 것.
"""
import sys
from pathlib import Path

import psycopg
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import SHARED_SCHEMA, get_settings
from app.db.session import engine

HERE = Path(__file__).parent
TEAM_DDL = HERE.parents[2] / "docs" / "hotel_reservation_ddl.sql"


DEV_SEED = "dev_seed.sql"  # 개발 · 테스트용 (테스트가 이 내용을 기준으로 확인한다)
DEMO_SEED = "demo_seed.sql"  # 시연용 40실 (공용 hotel)


def init_db(
    schema: str | None = None, seed: bool = True, reset_shared: bool = False, seed_file: str = DEV_SEED
) -> None:
    s = get_settings()
    schema = schema or s.db_schema
    if not s.db_reset_allowed:
        raise RuntimeError(".env에 DB_RESET_ALLOWED=true 가 있을 때만 스키마를 지우고 다시 만듭니다.")
    if schema == SHARED_SCHEMA and not reset_shared:
        raise RuntimeError(
            f"'{SHARED_SCHEMA}'는 시연 · 통합 확인용 공용 스키마입니다. .env의 DB_SCHEMA를 hotel_<이름>으로 바꾸거나,"
            " 팀에 알린 뒤 --reset-shared 를 붙여 실행하세요."
        )
    engine.dispose()  # 열려 있는 연결이 DROP SCHEMA를 막지 않게
    raw = engine.raw_connection()  # psycopg 연결: 세미콜론으로 이어진 여러 문장을 한 번에 실행할 수 있다
    try:
        with raw.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema}"')
            cur.execute(f'SET search_path TO "{schema}"')
            cur.execute(TEAM_DDL.read_text(encoding="utf-8"))
            if seed:
                cur.execute((HERE / seed_file).read_text(encoding="utf-8"))
        raw.commit()
    finally:
        raw.close()
        engine.dispose()  # 새 스키마로 다시 연결하게


if __name__ == "__main__":
    settings = get_settings()
    seed = "--no-seed" not in sys.argv
    seed_file = DEMO_SEED if "--demo" in sys.argv else DEV_SEED
    try:
        init_db(seed=seed, reset_shared="--reset-shared" in sys.argv, seed_file=seed_file)
        print(f"스키마 '{settings.db_schema}' 생성 완료" + (f" ({seed_file})" if seed else ""))
        if seed and settings.admin_password:
            from app.db.create_admin import DEV_ADMIN_ID, DEV_ADMIN_NAME, create_admin

            create_admin(DEV_ADMIN_ID, DEV_ADMIN_NAME, settings.admin_password)
            print(f"관리자 계정 '{DEV_ADMIN_ID}' 생성 완료")
        elif seed:
            print("관리자 계정 없음: .env에 ADMIN_PASSWORD를 넣고 다시 실행하면 admin01이 생깁니다.")
    except (SQLAlchemyError, psycopg.Error, ValueError, RuntimeError) as e:
        sys.exit(f"DB 초기화 실패: {e}")
