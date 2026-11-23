"""테스트는 로컬 MariaDB의 hotel_test DB를 매번 새로 만든다(.env 의 DB_NAME 은 건드리지 않음).

실행: uv run pytest  (backend 폴더에서)
"""
import os

os.environ["DB_NAME"] = "hotel_test"  # 앱 import 전에 (설정 · 엔진이 import 때 만들어짐)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.routes import members  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DB = "hotel_test"


@pytest.fixture
def client():
    members._fails.clear()
    return TestClient(app)


@pytest.fixture
def empty_db():
    """테이블만 있고 데이터 없음."""
    init_db(TEST_DB, seed=False)


@pytest.fixture
def seeded_db():
    """dev_seed.sql: 1번 ADMIN · 2번 USER(비밀번호 'not-a-real-hash'), 객실 5개, 12월 예약 3건."""
    init_db(TEST_DB, seed=True)
