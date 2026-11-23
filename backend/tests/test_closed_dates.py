"""휴무일(ADM-002): 시드 1번 = ADMIN, 2번 = USER. 쿠키는 로그인 대신 같은 방식으로 직접 만든다."""
from datetime import date, timedelta

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
API = "/api/admin/closed-dates"
TODAY = today_kst()
D1 = TODAY + timedelta(days=400)  # 시드(2026-12)와 겹치지 않는 미래 날짜


def add_reservation(room_id, check_in, nights, status="PENDING"):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO reservation (member_id, room_id, check_in_date, check_out_date, guest_count,"
                 " total_price, status) VALUES (2, :room, :cin, :cout, 1, 80000, :status)"),
            {"room": room_id, "cin": check_in, "cout": check_in + timedelta(days=nights), "status": status},
        )


def post(client, day, room_id=None, reason="시설 점검", headers=ADMIN):
    body = {"closedDate": day.isoformat(), "roomId": room_id, "reason": reason}
    return client.post(API, json=body, headers=headers)


def test_hotel_wide_close_then_list_then_release(client):
    r = post(client, D1)
    assert r.status_code == 201, r.text
    cid = r.json()["closedDateId"]
    assert r.json()["roomId"] is None

    listed = client.get(f"{API}?month={D1:%Y-%m}", headers=ADMIN).json()
    assert [c["closedDateId"] for c in listed] == [cid]

    assert client.delete(f"{API}/{cid}", headers=ADMIN).status_code == 204
    assert client.delete(f"{API}/{cid}", headers=ADMIN).status_code == 404


def test_reservation_blocks_closing_but_checkout_day_does_not(client):
    add_reservation(room_id=1, check_in=D1, nights=2)  # D1, D1+1 숙박. D1+2는 체크아웃
    r = post(client, D1 + timedelta(days=1))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "CLOSED_DATE_CONFLICT"
    assert "예약 1건" in r.json()["detail"]["message"]

    assert post(client, D1 + timedelta(days=2)).status_code == 201  # 체크아웃 날
    assert post(client, D1, room_id=2).status_code == 201  # 다른 방은 가능
    assert post(client, D1, room_id=1).status_code == 409  # 예약 있는 그 방은 불가


def test_canceled_reservation_does_not_block(client):
    add_reservation(room_id=1, check_in=D1, nights=1, status="CANCELED")
    assert post(client, D1).status_code == 201


def test_already_closed_rules(client):
    assert post(client, D1).status_code == 201
    assert post(client, D1).json()["detail"]["code"] == "ALREADY_CLOSED"
    assert post(client, D1, room_id=1).json()["detail"]["code"] == "ALREADY_CLOSED"  # 호텔 전체 휴무일
    assert post(client, D1 + timedelta(days=1), room_id=1).status_code == 201
    assert post(client, D1 + timedelta(days=1), room_id=1).status_code == 409


def test_input_and_permission_errors(client):
    assert post(client, TODAY - timedelta(days=1)).json()["detail"]["code"] == "PAST_DATE"
    assert post(client, TODAY).status_code == 201  # 오늘은 가능
    assert post(client, D1, reason="   ").status_code == 400
    assert post(client, D1, room_id=999).status_code == 404
    assert post(client, D1, headers=GUEST).status_code == 403
    assert post(client, D1, headers={}).status_code == 401


def post_range(client, start, end, room_id=None, reason="리모델링"):
    body = {"startDate": start.isoformat(), "endDate": end.isoformat(), "roomId": room_id, "reason": reason}
    return client.post(f"{API}/range", json=body, headers=ADMIN)


def test_range_creates_one_row_per_day(client):
    r = post_range(client, D1, D1 + timedelta(days=2), room_id=2)
    assert r.status_code == 201, r.text
    assert [(c["closedDate"], c["roomName"]) for c in r.json()] == [
        ((D1 + timedelta(days=i)).isoformat(), "102호") for i in range(3)]


def test_range_all_or_nothing(client):
    add_reservation(room_id=1, check_in=D1 + timedelta(days=2), nights=1)
    r = post_range(client, D1, D1 + timedelta(days=4))
    assert r.status_code == 409
    day = D1 + timedelta(days=2)
    assert r.json()["detail"]["message"] == f"{day.month}월 {day.day}일에 예약 1건이 있습니다. 먼저 예약을 취소해 주세요."
    assert client.get(f"{API}?month={D1:%Y-%m}", headers=ADMIN).json() == []  # 하루도 안 들어감

    assert post(client, D1 + timedelta(days=10)).status_code == 201
    r = post_range(client, D1 + timedelta(days=9), D1 + timedelta(days=11), room_id=3)
    assert r.json()["detail"]["code"] == "ALREADY_CLOSED"  # 중간에 호텔 전체 휴무


def test_range_input_errors(client):
    assert post_range(client, D1, D1 + timedelta(days=30)).status_code == 201  # 31일은 가능
    assert post_range(client, D1 + timedelta(days=40), D1 + timedelta(days=71)).json()["detail"]["code"] == "RANGE_TOO_LONG"
    assert post_range(client, D1 + timedelta(days=5), D1).status_code == 400  # 끝 < 시작
    assert post_range(client, TODAY - timedelta(days=1), TODAY).json()["detail"]["code"] == "PAST_DATE"
    assert post_range(client, D1 + timedelta(days=90), D1 + timedelta(days=91), room_id=999).status_code == 404


def test_screen_scenario_close_dec_31(client):
    """화면설계서 시나리오: 12월 달력 → 31일 클릭(예약 0건) → 사유 입력 후 지정 → ④ 목록에 생김."""
    def counts(q=""):
        return client.get(f"{API}/reservation-counts?month=2026-12{q}", headers=ADMIN).json()

    def closed(q=""):
        return client.get(f"{API}?month=2026-12{q}", headers=ADMIN).json()

    assert counts() == {
        "2026-12-15": 1, "2026-12-16": 1, "2026-12-17": 1,  # 101호 15~18 (승인)
        "2026-12-24": 1, "2026-12-25": 1,  # 201호 24~26 (대기)
    }  # 20일 취소 예약은 빠짐
    assert closed() == []  # ④ 처음엔 비어 있음
    assert "2026-12-31" not in counts()  # ③ "이 날 예약 0건"

    assert post(client, date(2026, 12, 31), reason="연말 시설 점검").status_code == 201
    assert post(client, date(2026, 12, 30), room_id=2, reason="102호 수리").status_code == 201

    rows = closed()
    assert [(c["closedDate"], c["roomName"], c["reason"]) for c in rows] == [
        ("2026-12-30", "102호", "102호 수리"), ("2026-12-31", None, "연말 시설 점검")]
    assert [c["roomId"] for c in closed("&roomId=1")] == [None]  # 101호 화면: 호텔 전체 휴무만
    assert set(counts("&roomId=1")) == {"2026-12-15", "2026-12-16", "2026-12-17"}

    assert post(client, date(2026, 12, 15)).json()["detail"]["message"] == \
        "이 날짜에 예약 1건이 있습니다. 먼저 예약을 취소해 주세요."
