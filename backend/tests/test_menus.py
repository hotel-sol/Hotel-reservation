"""상단 메뉴: 시드 1번 = ADMIN, 2번 = USER. 역할마다 그 역할 메뉴만, sort_order 순서로."""
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


def menus(client, headers=None):
    r = client.get("/api/menus", headers=headers or {})
    assert r.status_code == 200, r.text
    return [(m["menuName"], m["menuUrl"]) for m in r.json()]


def test_admin_sees_only_admin_menus_in_order(client):
    assert menus(client, ADMIN) == ADMIN_MENUS


def test_user_and_anonymous_see_only_user_menus(client):
    assert menus(client, GUEST) == USER_MENUS
    assert menus(client) == USER_MENUS


def test_broken_cookie_is_treated_as_anonymous(client):
    assert menus(client, {"Cookie": f"{COOKIE}=not-a-valid-token"}) == USER_MENUS
