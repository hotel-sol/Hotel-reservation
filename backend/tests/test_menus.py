"""상단 메뉴: 시드 1번 = ADMIN, 2번 = USER.

손님 · 비로그인 = 손님 메뉴만. 관리자 = 손님 메뉴 + 관리자 메뉴(role 로 구분, 각 묶음은 sort_order 순).
"""
import pytest

from app.core.config import get_settings
from app.core.security import create_session_token

pytestmark = pytest.mark.usefixtures("seeded_db")

SEED_PASSWORD = "not-a-real-hash"
COOKIE = get_settings().session_cookie
ADMIN = {"Cookie": f"{COOKIE}={create_session_token(1, SEED_PASSWORD)}"}
GUEST = {"Cookie": f"{COOKIE}={create_session_token(2, SEED_PASSWORD)}"}
USER_MENUS = [("객실 추천", "/rooms"), ("내 예약", "/reservation/list")]
ADMIN_MENUS = [
    ("객실 관리", "/admin/rooms"),
    ("예약 일자 관리", "/admin/closed-dates"),
    ("예약 관리", "/admin/reservations"),
]


def menus(client, headers=None, role=None):
    r = client.get("/api/menus", headers=headers or {})
    assert r.status_code == 200, r.text
    return [(m["menuName"], m["menuUrl"]) for m in r.json() if role is None or m["role"] == role]


def test_admin_gets_both_groups_each_in_order(client):
    # 화면은 /admin/* 에서 ADMIN 묶음, 그 밖에서 USER 묶음만 보여준다
    assert menus(client, ADMIN, role="USER") == USER_MENUS
    assert menus(client, ADMIN, role="ADMIN") == ADMIN_MENUS
    assert menus(client, ADMIN) == USER_MENUS + ADMIN_MENUS  # 섞이지 않고 묶음별로


def test_user_and_anonymous_see_only_user_menus(client):
    assert menus(client, GUEST) == USER_MENUS
    assert menus(client) == USER_MENUS


def test_broken_cookie_is_treated_as_anonymous(client):
    assert menus(client, {"Cookie": f"{COOKIE}=not-a-valid-token"}) == USER_MENUS
