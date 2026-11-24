"""객실 예약(RSV-001) · 막힌 이유별 오류(Step 2 4A).

시드 1번 = ADMIN, 2번 = USER. 객실 1(101호, 2명, 80000원) · 2(102호) · 5(401호, 판매 안 함).
쿠키는 로그인 대신 같은 방식으로 직접 만든다(test_closed_dates.py 와 같음).
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
GUEST = {"Cookie": f"{COOKIE}={create_session_token(2, SEED_PASSWORD)}"}
API = "/api/reservations"
TODAY = today_kst()
D1 = TODAY + timedelta(days=400)  # 시드(2026-12)와 겹치지 않는 미래 날짜


def sql(statement, **params):
    with engine.begin() as conn:
        conn.execute(text(statement), params)


def add_reservation(room_id, check_in, nights, status="PENDING"):
    sql("INSERT INTO reservation (member_id, room_id, check_in_date, check_out_date, guest_count,"
        " total_price, status) VALUES (2, :room, :cin, :cout, 1, 80000, :status)",
        room=room_id, cin=check_in, cout=check_in + timedelta(days=nights), status=status)


def close(day, room_id=None):
    """room_id 가 None 이면 호텔 전체 휴무, 있으면 그 객실만 판매 중지."""
    sql("INSERT INTO closed_date (room_id, closed_date, reason) VALUES (:room, :day, '테스트')",
        room=room_id, day=day)


def reserve(client, check_in, nights=2, room_id=1, guests=2, headers=GUEST):
    body = {
        "roomId": room_id,
        "checkInDate": check_in.isoformat(),
        "checkOutDate": (check_in + timedelta(days=nights)).isoformat(),
        "guestCount": guests,
    }
    return client.post(API, json=body, headers=headers)


def code(r):
    return r.json()["detail"]["code"]


def test_create_reservation_saves_price_and_pending(client):
    r = reserve(client, D1, nights=3)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "PENDING"
    assert body["totalPrice"] == 80000 * 3  # room.price * 박수
    assert body["roomName"] == "101호"


def test_overlap_is_room_not_available(client):
    add_reservation(room_id=1, check_in=D1, nights=2)  # D1, D1+1 숙박. D1+2 는 체크아웃
    r = reserve(client, D1 + timedelta(days=1))
    assert r.status_code == 409
    assert code(r) == "ROOM_NOT_AVAILABLE"
    assert r.json()["detail"]["message"] == "선택한 날짜에 이미 예약이 있습니다."

    assert reserve(client, D1 - timedelta(days=1), nights=1).status_code == 201  # 체크인 날에 체크아웃
    assert reserve(client, D1 + timedelta(days=2)).status_code == 201  # 체크아웃 날에 체크인
    assert reserve(client, D1, room_id=2).status_code == 201  # 다른 방은 가능


def test_canceled_reservation_does_not_block(client):
    add_reservation(room_id=1, check_in=D1, nights=2, status="CANCELED")
    assert reserve(client, D1).status_code == 201


def test_hotel_closed_is_date_closed(client):
    close(D1 + timedelta(days=1))  # 호텔 전체 휴무
    r = reserve(client, D1, nights=3)
    assert r.status_code == 409
    assert code(r) == "DATE_CLOSED"
    assert r.json()["detail"]["message"] == "선택한 기간에 호텔 휴무일이 있어 예약할 수 없습니다."
    assert code(reserve(client, D1, room_id=2, nights=3)) == "DATE_CLOSED"  # 모든 방이 막힘


def test_room_closed_is_room_closed(client):
    close(D1 + timedelta(days=1), room_id=1)  # 101호만 판매 중지
    r = reserve(client, D1, nights=3)
    assert r.status_code == 409
    assert code(r) == "ROOM_CLOSED"
    assert r.json()["detail"]["message"] == "이 객실은 선택한 기간에 판매하지 않습니다."
    assert reserve(client, D1, room_id=2, nights=3).status_code == 201  # 다른 방은 가능


def test_closed_on_checkout_day_does_not_block(client):
    close(D1 + timedelta(days=2))  # 체크아웃 날은 묵지 않으므로 괜찮음
    close(D1 + timedelta(days=2), room_id=1)
    assert reserve(client, D1, nights=2).status_code == 201


def test_block_reason_order(client):
    """여러 이유가 겹치면 DATE_CLOSED > ROOM_CLOSED > ROOM_NOT_AVAILABLE 순서로 하나만."""
    add_reservation(room_id=1, check_in=D1, nights=1)
    close(D1, room_id=1)
    assert code(reserve(client, D1)) == "ROOM_CLOSED"
    close(D1)
    assert code(reserve(client, D1)) == "DATE_CLOSED"


def test_input_errors(client):
    r = reserve(client, TODAY - timedelta(days=1))
    assert r.status_code == 400 and code(r) == "PAST_DATE"
    assert reserve(client, TODAY).status_code == 201  # 오늘 체크인은 가능

    r = reserve(client, D1, guests=3)  # 101호 최대 2명
    assert r.status_code == 400 and code(r) == "TOO_MANY_GUESTS"

    assert code(reserve(client, D1, room_id=5)) == "ROOM_NOT_FOUND"  # 판매 안 하는 401호
    assert code(reserve(client, D1, room_id=999)) == "ROOM_NOT_FOUND"
    assert reserve(client, D1, nights=0).status_code == 422  # 체크아웃 = 체크인
    assert reserve(client, D1, headers={}).status_code == 401  # 로그인 안 함


# ---- 요금 견적 (Step 2 4C): GET /api/rooms/{id}/quote ----

def quote(client, check_in, nights=2, room_id=1, guests=2):
    check_out = check_in + timedelta(days=nights)
    return client.get(f"/api/rooms/{room_id}/quote?checkIn={check_in}&checkOut={check_out}&guests={guests}")


def test_quote_matches_saved_reservation(client):
    r = quote(client, D1, nights=3, room_id=3)  # 201호 120000원
    assert r.status_code == 200, r.text
    assert r.json() == {
        "roomId": 3, "checkIn": D1.isoformat(), "checkOut": (D1 + timedelta(days=3)).isoformat(),
        "guests": 2, "nights": 3, "pricePerNight": 120000, "totalPrice": 360000,
    }
    saved = reserve(client, D1, nights=3, room_id=3)  # 같은 조건으로 저장하면 같은 금액
    assert saved.json()["totalPrice"] == r.json()["totalPrice"]


def test_quote_works_without_login(client):
    assert quote(client, D1).status_code == 200  # 쿠키 없이도 금액은 볼 수 있음


def test_quote_errors_same_as_reservation(client):
    r = quote(client, D1, nights=0)
    assert r.status_code == 400 and code(r) == "INVALID_DATES"
    assert code(quote(client, D1, nights=-1)) == "INVALID_DATES"
    assert code(quote(client, D1, guests=3)) == "TOO_MANY_GUESTS"
    assert code(reserve(client, D1, guests=3)) == "TOO_MANY_GUESTS"
    assert code(quote(client, TODAY - timedelta(days=1))) == "PAST_DATE"
    assert code(reserve(client, TODAY - timedelta(days=1))) == "PAST_DATE"
    assert code(quote(client, D1, room_id=5)) == "ROOM_NOT_FOUND"
    assert quote(client, D1, guests=0).status_code == 422
    assert client.get("/api/rooms/1/quote").status_code == 422  # 날짜 · 인원 빠짐
