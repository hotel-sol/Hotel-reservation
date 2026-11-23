"""테스트는 팀 Supabase 프로젝트 안의 <내 스키마>_test 스키마를 매번 새로 만든다.

예: .env 의 DB_SCHEMA=hotel_minhyuk → 테스트는 hotel_minhyuk_test. 다른 사람 스키마와 공용 hotel 은 건드리지 않는다.
실행: uv run pytest  (backend 폴더에서, .env 에 DATABASE_URL · DB_SCHEMA=hotel_<이름> · DB_RESET_ALLOWED=true 필요)
"""
import os

from app.core.config import SHARED_SCHEMA, Settings

_mine = Settings().db_schema
if _mine == SHARED_SCHEMA:
    raise RuntimeError("테스트 전에 .env 의 DB_SCHEMA 를 hotel_<이름> 으로 정해 주세요(공용 hotel 과 겹치지 않게).")
os.environ["DB_SCHEMA"] = f"{_mine}_test"  # 앱 import 전에 (설정 · 엔진이 import 때 만들어짐)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.routes import members  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    members._fails.clear()
    return TestClient(app)


@pytest.fixture
def empty_db():
    """테이블만 있고 데이터 없음."""
    init_db(seed=False)


@pytest.fixture
def seeded_db():
    """dev_seed.sql: 1번 ADMIN · 2번 USER(비밀번호 'not-a-real-hash'), 객실 5개, 12월 예약 3건."""
    init_db(seed=True)
