"""조회수 하루 1회(1-A1): 같은 사람 · 같은 방 · 같은 날은 1번만 센다."""
import pytest
from sqlalchemy import text

from app.api.routes.rooms import VISITOR_COOKIE
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


def test_guest_counted_once_a_day_with_ticket_cookie(client, rooms):
    r = view(client)
    assert r.status_code == 204
    ticket = r.cookies.get(VISITOR_COOKIE)
    assert ticket and len(ticket) == 32  # 비회원 번호표를 준다
    assert view(client).status_code == 204 and view(client).status_code == 204
    assert views() == 1  # 같은 손님 · 같은 날은 1번
    assert view(client, 2).status_code == 204 and views(2) == 1  # 다른 방은 따로 센다

    client.cookies.clear()  # 다른 손님(번호표 없음)
    view(client)
    assert views() == 2

    run("UPDATE room_view SET view_date = view_date - 1")  # 다음 날이 되면 다시 센다
    client.cookies.set(VISITOR_COOKIE, ticket)
    view(client)
    assert views() == 3


def test_member_counted_by_member_not_cookie(client, rooms):
    client.post("/api/members/signup", json={"loginId": "guest01", "password": "password123", "name": "손님"})
    client.post("/api/members/login", json={"loginId": "guest01", "password": "password123"})
    view(client)
    client.cookies.set(VISITOR_COOKIE, "0" * 32)  # 번호표가 바뀌어도 회원은 회원 번호로 센다
    view(client)
    assert views() == 1
    assert run("SELECT viewer_key FROM room_view").scalar_one().startswith("M:")


def test_forged_ticket_is_replaced_and_missing_room_404(client, rooms):
    client.cookies.set(VISITOR_COOKIE, "<script>")
    r = view(client)
    assert r.cookies.get(VISITOR_COOKIE) not in (None, "<script>")  # 이상한 값은 새 번호표로
    assert view(client, 999).status_code == 404
