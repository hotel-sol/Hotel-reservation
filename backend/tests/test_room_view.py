"""조회수 하루 1회(1-A1): 같은 사람 · 같은 방 · 같은 날은 1번만 센다. 비회원은 모두 합쳐 한 사람으로."""
import pytest
from sqlalchemy import text

from app.db.session import engine

pytestmark = pytest.mark.usefixtures("empty_db")


def run(statement, **params):
    with engine.begin() as conn:
        return conn.execute(text(statement), params)


def views(room_id=1):
    return run("SELECT view_count FROM room WHERE room_id = :r", r=room_id).scalar_one()


@pytest.fixture
def rooms():
    run("INSERT INTO room (room_name, room_type, max_guest, price) VALUES ('101호', 'STANDARD', 2, 80000), "
        "('102호', 'STANDARD', 2, 80000)")


def view(client, room_id=1):
    return client.post(f"/api/rooms/{room_id}/view")


def test_guests_together_counted_once_a_day(client, rooms):
    """비회원은 모두 합쳐 방마다 하루 1번: 쿠키를 버리고 계속 불러도 부풀릴 수 없다(#67-2)."""
    for _ in range(3):
        client.cookies.clear()  # 매번 다른 손님인 척
        assert view(client).status_code == 204
    assert views() == 1
    assert view(client, 2).status_code == 204 and views(2) == 1  # 다른 방은 따로 센다

    run("UPDATE room_view SET view_date = view_date - 1")  # 다음 날이 되면 다시 센다
    view(client)
    assert views() == 2


def test_each_member_counted_once_a_day(client, rooms):
    view(client)  # 비회원 1
    for login_id in ("guest01", "guest02"):
        client.post("/api/members/signup", json={"loginId": login_id, "password": "password123", "name": "손님"})
        client.post("/api/members/login", json={"loginId": login_id, "password": "password123"})
        view(client)
        view(client)  # 같은 회원 · 같은 날은 1번
    assert views() == 3
    assert sorted(r[0][:2] for r in run("SELECT viewer_key FROM room_view")) == ["G", "M:", "M:"]


def test_missing_or_hidden_room_404(client, rooms):
    run("UPDATE room SET is_active = 'N' WHERE room_id = 2")
    assert view(client, 2).status_code == 404
    assert view(client, 999).status_code == 404


def test_huge_page_number_is_422_not_500(client):
    assert client.get("/api/rooms/recommend", params={"page": 10**20}).status_code == 422
