"""시연용 데이터 demo_seed.sql (Step 2 · 2C) — 객실상품 검토안 v1.9 의 40실이 그대로 들어가는지."""
from collections import Counter
from pathlib import Path

import pytest
from sqlalchemy import text

from app.db.init_db import DEMO_SEED, init_db
from app.db.session import engine

PUBLIC = Path(__file__).resolve().parents[2] / "frontend" / "public"


@pytest.fixture
def demo_db():
    init_db(seed_file=DEMO_SEED)


def rows(sql):
    with engine.connect() as c:
        return c.execute(text(sql)).all()


def test_forty_rooms_by_grade(demo_db):
    rooms = rows("SELECT room_name, room_type, max_guest, price, is_active FROM room")
    assert len(rooms) == 40
    assert Counter(r.room_type for r in rooms) == {"로얄 스위트": 2, "이그제큐티브 스위트": 6, "프리미어": 12, "디럭스": 20}
    assert {r.room_type: r.max_guest for r in rooms} == {"로얄 스위트": 6, "이그제큐티브 스위트": 3, "프리미어": 3, "디럭스": 2}
    assert all(r.is_active == "Y" for r in rooms)


def test_prices_follow_view_rule(demo_db):
    """비수기 요금 = 기준가 × 전망 배율 (리버뷰 1.1)."""
    price = {r.room_name: r.price for r in rows("SELECT room_name, price FROM room")}
    assert price["1601호"] == 4_400_000 and price["1602호"] == 4_000_000  # S 리버 · 시티
    assert price["1501호"] == 1_320_000 and price["1502호"] == 1_200_000  # A
    assert price["1201호"] == 770_000 and price["1204호"] == 700_000  # B 리버 · 마운틴
    assert price["0501호"] == 605_000 and price["0504호"] == 550_000  # C 리버 · 마운틴


def test_photos_one_to_five_per_room_and_files_exist(demo_db):
    files = rows("SELECT target_id, saved_path FROM attach_file WHERE target_type = 'ROOM'")
    per_room = Counter(f.target_id for f in files)
    assert len(per_room) == 40 and all(1 <= n <= 5 for n in per_room.values())
    for f in files:
        assert f.saved_path.startswith("room-photos/")
        assert (PUBLIC / f.saved_path).is_file(), f.saved_path


def test_recommend_shows_demo_rooms_with_thumbnails(client, demo_db):
    items = client.get("/api/rooms/recommend", params={"size": 50}).json()["items"]
    assert len(items) == 40
    assert all(i["thumbnailUrl"] and i["thumbnailUrl"].startswith("room-photos/") for i in items)
    assert sum(i["isRecommended"] for i in items) == 3  # 추천 점수 1~3위 (BEST)
