"""객실 관리 Step 2 · 2A — 미래 예약 객실의 종류 · 인원 · 요금 수정 거부, 목록 요약.

시드 1번 = ADMIN, 2번 = USER, 객실 1~5번(5번은 비활성). 시드 예약은 지우고 오늘 기준 날짜로 새로 넣는다.
"""
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.dates import today_kst
from app.core.security import create_session_token
from app.db.session import engine

pytestmark = pytest.mark.usefixtures("seeded_db")

SEED_PASSWORD = "not-a-real-hash"
COOKIE = get_settings().session_cookie
ADMIN = {"Cookie": f"{COOKIE}={create_session_token(1, SEED_PASSWORD)}"}
GUEST = {"Cookie": f"{COOKIE}={create_session_token(2, SEED_PASSWORD)}"}
TODAY = today_kst()


@pytest.fixture(autouse=True)
def no_seed_reservations(seeded_db):
    run("DELETE FROM reservation")


def run(sql, **params):
    with engine.begin() as conn:
        conn.execute(text(sql), params)


def reserve(room_id, check_in, nights=1, status="APPROVED"):
    run(
        "INSERT INTO reservation (member_id, room_id, check_in_date, check_out_date, guest_count, total_price, status)"
        " VALUES (2, :room, :cin, :cout, 1, 80000, :status)",
        room=room_id, cin=check_in, cout=check_in + timedelta(days=nights), status=status,
    )


def close(day, room_id=None):
    run("INSERT INTO closed_date (room_id, closed_date, reason) VALUES (:room, :day, '점검')", room=room_id, day=day)


def room1(**change):
    body = {"roomName": "101호", "roomType": "STANDARD", "maxGuest": 2, "price": 80000, "description": "시티뷰"}
    return {**body, **change}


def put(client, body, room_id=1):
    return client.put(f"/api/admin/rooms/{room_id}", json=body, headers=ADMIN)


# ---------- 미래 예약이 있으면 종류 · 인원 · 요금 수정 거부 ----------

@pytest.mark.parametrize("change", [{"price": 90000}, {"maxGuest": 3}, {"roomType": "DELUXE"}])
def test_future_reservation_blocks_type_guest_price(client, change):
    reserve(1, TODAY + timedelta(days=10))
    r = put(client, room1(**change))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "FUTURE_RESERVATION_EXISTS"
    assert "1건" in r.json()["detail"]["message"]


def test_name_and_description_still_editable(client):
    reserve(1, TODAY + timedelta(days=10))
    r = put(client, room1(roomName="101호(리모델링)", description="시티뷰 · 새 단장"))
    assert r.status_code == 200, r.text
    assert r.json()["roomName"] == "101호(리모델링)"


def test_staying_now_counts_as_future(client):
    """어제 체크인 · 내일 체크아웃 = 지금 묵는 중 → 바꿀 수 없음."""
    reserve(1, TODAY - timedelta(days=1), nights=2)
    assert put(client, room1(price=90000)).status_code == 409


@pytest.mark.parametrize("check_in,nights,status", [
    (TODAY - timedelta(days=3), 3, "APPROVED"),   # 오늘 체크아웃 = 끝난 예약
    (TODAY - timedelta(days=10), 2, "APPROVED"),  # 지난 예약
    (TODAY + timedelta(days=10), 1, "CANCELED"),  # 취소된 예약
])
def test_past_or_canceled_reservation_does_not_block(client, check_in, nights, status):
    reserve(1, check_in, nights, status)
    r = put(client, room1(price=90000))
    assert r.status_code == 200, r.text
    assert r.json()["price"] == 90000


def test_pending_reservation_also_blocks(client):
    reserve(1, TODAY + timedelta(days=5), status="PENDING")
    assert put(client, room1(maxGuest=4)).status_code == 409


def test_other_room_reservation_does_not_block(client):
    reserve(2, TODAY + timedelta(days=5))
    assert put(client, room1(price=90000)).status_code == 200


# ---------- 목록 요약 ----------

def summary(client, headers=ADMIN):
    r = client.get("/api/admin/rooms/summary", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_summary_without_closures(client):
    s = summary(client)
    assert (s["total"], s["onSale"], s["closedToday"], s["closedSoon"], s["inactive"]) == (5, 4, 0, 0, 1)


def test_summary_room_closures_today_and_soon(client):
    close(TODAY, room_id=1)
    close(TODAY + timedelta(days=3), room_id=2)
    close(TODAY - timedelta(days=1), room_id=3)  # 어제 휴무는 셈하지 않음
    close(TODAY, room_id=5)  # 비활성 객실의 휴무는 셈하지 않음
    s = summary(client)
    assert (s["onSale"], s["closedToday"], s["closedSoon"], s["inactive"]) == (3, 1, 1, 1)
    assert s["closedTodayRoomIds"] == [1] and s["closedSoonRoomIds"] == [2]


def test_summary_hotel_wide_closure_today(client):
    close(TODAY)  # 호텔 전체 → 사용 중 객실 4개 모두
    close(TODAY + timedelta(days=2), room_id=2)  # 오늘 이미 휴무인 방은 '예정'에 넣지 않음
    s = summary(client)
    assert (s["onSale"], s["closedToday"], s["closedSoon"]) == (0, 4, 0)
    assert s["closedTodayRoomIds"] == [1, 2, 3, 4]


def test_summary_hotel_wide_closure_soon(client):
    close(TODAY + timedelta(days=7))
    s = summary(client)
    assert (s["onSale"], s["closedToday"], s["closedSoon"]) == (4, 0, 4)


def test_admin_only(client):
    assert client.get("/api/admin/rooms/summary").status_code == 401
    assert client.get("/api/admin/rooms/summary", headers=GUEST).status_code == 403
