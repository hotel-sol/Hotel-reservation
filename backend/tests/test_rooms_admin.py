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
from tests import helpers

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
    helpers.add_reservation(room_id, check_in, nights, status, total_price=80000)


def close(day, room_id=None):
    helpers.add_closed_date(day, room_id, "점검")


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


# ---------- 2-A1 등급 · 전망 · 침대 ----------

def grades(client):
    r = client.get("/api/room-grades")  # 로그인 없이 읽기
    assert r.status_code == 200, r.text
    return {g["gradeCode"]: g for g in r.json()}


def test_room_grades_list(client):
    r = client.get("/api/room-grades")
    assert [g["gradeCode"] for g in r.json()] == ["S", "A", "B", "C"]  # sort_order 순
    c = grades(client)["C"]
    assert (c["gradeName"], c["basePrice"], c["maxGuest"], c["areaM2"]) == ("디럭스", 550000, 2, 40)


def test_create_room_with_grade_sets_room_type(client):
    deluxe = grades(client)["C"]
    body = {"roomName": "0777호", "roomType": "아무 글자", "maxGuest": 2, "price": 605000,
            "gradeId": deluxe["gradeId"], "viewType": "RIVER", "bedType": "트윈"}
    r = client.post("/api/admin/rooms", json=body, headers=ADMIN)
    assert r.status_code == 201, r.text
    room = r.json()
    assert room["roomType"] == "디럭스"  # 등급 이름으로 맞춤 (1 · 4 · 5번이 읽는 글자)
    assert (room["gradeId"], room["viewType"], room["bedType"]) == (deluxe["gradeId"], "RIVER", "트윈")


def test_create_room_without_grade_still_works(client):
    r = client.post("/api/admin/rooms", json=room1(roomName="0778호"), headers=ADMIN)
    assert r.status_code == 201, r.text
    assert (r.json()["roomType"], r.json()["gradeId"], r.json()["viewType"]) == ("STANDARD", None, None)


def test_unknown_grade_rejected(client):
    r = client.post("/api/admin/rooms", json=room1(roomName="0779호", gradeId=99999), headers=ADMIN)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "GRADE_NOT_FOUND"


def test_unknown_view_rejected(client):
    r = client.post("/api/admin/rooms", json=room1(roomName="0779호", viewType="OCEAN"), headers=ADMIN)
    assert r.status_code == 422


def test_future_reservation_blocks_grade_change(client):
    reserve(1, TODAY + timedelta(days=10))
    r = put(client, room1(gradeId=grades(client)["C"]["gradeId"]))  # STANDARD → 디럭스
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "FUTURE_RESERVATION_EXISTS"


def test_future_reservation_allows_view_and_bed_change(client):
    reserve(1, TODAY + timedelta(days=10))
    r = put(client, room1(viewType="CITY", bedType="킹"))  # 요금 · 인원 · 종류 그대로
    assert r.status_code == 200, r.text
    assert (r.json()["viewType"], r.json()["bedType"]) == ("CITY", "킹")
