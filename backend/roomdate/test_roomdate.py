"""휴무일 API 통과 테스트. 실제 MariaDB의 hotel_test DB를 매번 새로 만든다.

실행: DB_PORT=3307 python -m pytest -q  (backend/roomdate 폴더에서)
"""
import os

os.environ["DB_NAME"] = "hotel_test"  # db.py import 전에

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

import roomdate as app_module
from roomdate import connect
from init_db import init_db

ADMIN = {"X-Member-Id": "1"}
GUEST = {"X-Member-Id": "2"}
client = TestClient(app_module.app)
TODAY = app_module.today_kst()
D1 = TODAY + timedelta(days=400)  # 시드(2026-12)와 겹치지 않는 미래 날짜


@pytest.fixture(autouse=True)
def fresh_db():
    init_db("hotel_test")


def add_reservation(room_id, check_in, nights, status="PENDING"):
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO RESERVATION (member_id, room_id, check_in_date, check_out_date,"
            " guest_count, total_price, status) VALUES (2, %s, %s, %s, 1, 80000, %s)",
            (room_id, check_in, check_in + timedelta(days=nights), status),
        )
    conn.commit()
    conn.close()


def post(day, room_id=None, reason="시설 점검", headers=ADMIN):
    body = {"closedDate": day.isoformat(), "roomId": room_id, "reason": reason}
    return client.post("/admin/closed-dates", json=body, headers=headers)


def test_hotel_wide_close_then_list_then_release():
    r = post(D1)
    assert r.status_code == 201, r.text
    cid = r.json()["closedDateId"]
    assert r.json()["roomId"] is None

    month = D1.strftime("%Y-%m")
    listed = client.get(f"/admin/closed-dates?month={month}", headers=ADMIN).json()
    assert [c["closedDateId"] for c in listed["closedDates"]] == [cid]

    assert client.delete(f"/admin/closed-dates/{cid}", headers=ADMIN).status_code == 204
    assert client.delete(f"/admin/closed-dates/{cid}", headers=ADMIN).status_code == 404


def test_reservation_blocks_closing_but_checkout_day_does_not():
    add_reservation(room_id=1, check_in=D1, nights=2)  # D1, D1+1 숙박. D1+2는 체크아웃
    r = post(D1 + timedelta(days=1))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "CLOSED_DATE_CONFLICT"
    assert "예약 1건" in r.json()["detail"]["message"]

    assert post(D1 + timedelta(days=2)).status_code == 201   # 체크아웃 날
    assert post(D1, room_id=2).status_code == 201            # 다른 방은 가능
    assert post(D1, room_id=1).status_code == 409            # 예약 있는 그 방은 불가


def test_canceled_reservation_does_not_block():
    add_reservation(room_id=1, check_in=D1, nights=1, status="CANCELED")
    assert post(D1).status_code == 201


def test_already_closed_rules():
    assert post(D1).status_code == 201
    assert post(D1).json()["detail"]["code"] == "ALREADY_CLOSED"
    assert post(D1, room_id=1).json()["detail"]["code"] == "ALREADY_CLOSED"  # 호텔 전체 휴무일
    assert post(D1 + timedelta(days=1), room_id=1).status_code == 201
    assert post(D1 + timedelta(days=1), room_id=1).status_code == 409


def test_input_and_permission_errors():
    assert post(TODAY - timedelta(days=1)).json()["detail"]["code"] == "PAST_DATE"
    assert post(TODAY).status_code == 201                    # 오늘은 가능
    assert post(D1, reason="   ").status_code == 400
    assert post(D1, room_id=999).status_code == 404
    assert post(D1, headers=GUEST).status_code == 403
    assert post(D1, headers={}).status_code == 401


def test_month_counts_match_screen_example():
    listed = client.get("/admin/closed-dates?month=2026-12", headers=ADMIN).json()
    assert listed["reservationCounts"] == {
        "2026-12-15": 1, "2026-12-16": 1, "2026-12-17": 1,   # 101호 15~18 (승인)
        "2026-12-24": 1, "2026-12-25": 1,                    # 201호 24~26 (대기)
    }                                                        # 20일 취소 예약은 빠짐
    assert [c["closedDate"] for c in listed["closedDates"]] == ["2026-12-31"]

    room1 = client.get("/admin/closed-dates?month=2026-12&roomId=1", headers=ADMIN).json()
    assert set(room1["reservationCounts"]) == {"2026-12-15", "2026-12-16", "2026-12-17"}
    assert room1["closedDates"][0]["roomId"] is None         # 호텔 전체 휴무는 방별 화면에도 보임
