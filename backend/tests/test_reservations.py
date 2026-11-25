"""객실 예약(RSV-001) · 막힌 이유별 오류(Step 2 4A).

시드 1번 = ADMIN, 2번 = USER. 객실 1(101호, 2명, 80000원) · 2(102호) · 5(401호, 판매 안 함).
쿠키는 로그인 대신 같은 방식으로 직접 만든다(test_closed_dates.py 와 같음).
"""
from datetime import date, timedelta

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
GUEST = {"Cookie": f"{COOKIE}={create_session_token(2, SEED_PASSWORD)}"}
API = "/api/reservations"
REAL_TODAY = today_kst()
# 시드(2026-12 예약)와 겹치지 않는 미래 날짜
D1 = max(REAL_TODAY + timedelta(days=30), date(2027, 1, 4))
# 예약 확인(reservation_service)이 보는 '오늘'. 예약 가능 범위(오늘부터 30일) 안에 D1 이 들어오게 D1 사흘 전으로 고정한다.
TODAY = D1 - timedelta(days=3)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("app.services.reservation_service.today_kst", lambda: TODAY)


def sql(statement, **params):
    with engine.begin() as conn:
        conn.execute(text(statement), params)


def add_reservation(room_id, check_in, nights, status="PENDING"):
    helpers.add_reservation(room_id, check_in, nights, status, total_price=80000)


def close(day, room_id=None):
    """room_id 가 None 이면 호텔 전체 휴무, 있으면 그 객실만 판매 중지."""
    helpers.add_closed_date(day, room_id)


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
    # D1, D1+1 숙박. D1+2 는 체크아웃. 다른 회원(1번)의 예약으로 둬서 guest1 의 대기 예약 상한(#68)에 안 걸리게
    helpers.add_reservation(1, D1, 2, total_price=80000, member_id=1)
    r = reserve(client, D1 + timedelta(days=1))
    assert r.status_code == 409
    assert code(r) == "ROOM_NOT_AVAILABLE"
    assert r.json()["detail"]["message"] == "선택한 날짜에 이미 예약이 있습니다."

    assert reserve(client, D1 - timedelta(days=1), nights=1).status_code == 201  # 체크인 날에 체크아웃
    assert reserve(client, D1 + timedelta(days=2)).status_code == 201  # 체크아웃 날에 체크인
    # 다른 방은 가능 (guest1 은 위 2건 등으로 대기 상한(#68)에 가까워서 1번 회원으로 확인)
    assert reserve(client, D1, room_id=2, headers=ADMIN).status_code == 201


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


# ---- 취소된 예약의 날짜가 달력에서 다시 열리는지 (남은 일 6) ----

ADMIN = {"Cookie": f"{COOKIE}={create_session_token(1, SEED_PASSWORD)}"}


def calendar(client, day, room_id=1):
    """day 가 속한 달의 달력에서 {날짜: reason} 만 뽑는다."""
    r = client.get(f"/api/rooms/{room_id}/available-dates?month={day:%Y-%m}")
    assert r.status_code == 200, r.text
    return {d["day"]: d["reason"] for d in r.json()["days"]}


@pytest.mark.parametrize("approve_first", [False, True], ids=["pending", "approved"])
def test_canceled_reservation_reopens_calendar(client, approve_first):
    # 2박(체크아웃 포함 사흘)이 한 달 달력 안에 들어오는 날. 넘치면 다음 달 1일 (그래도 예약 가능 범위 안)
    day = D1 if (D1 + timedelta(days=2)).month == D1.month else (D1 + timedelta(days=5)).replace(day=1)
    r = reserve(client, day, nights=2)
    assert r.status_code == 201, r.text
    rid = r.json()["reservationId"]
    if approve_first:
        assert client.patch(f"/api/admin/reservations/{rid}/approve", headers=ADMIN).status_code == 200

    cal = calendar(client, day)
    assert [cal[(day + timedelta(days=i)).isoformat()] for i in range(3)] == ["BOOKED", "BOOKED", None]
    assert code(reserve(client, day, nights=1)) == "ROOM_NOT_AVAILABLE"

    assert client.patch(f"/api/admin/reservations/{rid}/cancel", headers=ADMIN).json()["status"] == "CANCELED"

    cal = calendar(client, day)
    assert [cal[(day + timedelta(days=i)).isoformat()] for i in range(3)] == [None, None, None]
    assert reserve(client, day, nights=2).status_code == 201  # 같은 날짜를 다시 예약할 수 있음


def test_seed_canceled_reservation_is_open(client):
    """시드: 102호 2026-12-20~21 예약은 CANCELED 라서 20일이 열려 있어야 한다."""
    if REAL_TODAY > date(2026, 12, 20):
        pytest.skip("시드 날짜가 이미 지남")
    cal = calendar(client, date(2026, 12, 20), room_id=2)
    assert cal["2026-12-20"] is None


# ---- 예약 가능 범위: 최대 박수 · 체크인 가능 기간 (fix/reservation-limits) ----

from app.services.reservation_service import BOOKING_WINDOW_DAYS, MAX_NIGHTS  # noqa: E402


def test_max_nights(client):
    assert quote(client, D1, nights=MAX_NIGHTS).status_code == 200  # 최대 박수(6박)는 가능
    r = quote(client, D1, nights=MAX_NIGHTS + 1)
    assert r.status_code == 400 and code(r) == "TOO_LONG_STAY"
    assert code(reserve(client, D1, nights=MAX_NIGHTS + 1)) == "TOO_LONG_STAY"
    # 예전에는 몇십 년 예약이 저장되거나 총액이 INT 한도를 넘어 500 이 났다
    r = reserve(client, TODAY, nights=7305)
    assert r.status_code == 400 and code(r) == "TOO_LONG_STAY"


def test_booking_window(client):
    last = TODAY + timedelta(days=BOOKING_WINDOW_DAYS)
    assert quote(client, last, nights=1).status_code == 200  # 30일째 체크인은 가능
    r = quote(client, last + timedelta(days=1), nights=1)
    assert r.status_code == 400 and code(r) == "TOO_FAR_DATE"
    assert code(reserve(client, last + timedelta(days=1), nights=1)) == "TOO_FAR_DATE"


def test_calendar_rejects_bad_year(client):
    for month in ("0000-01", "1999-12", "2101-01"):
        r = client.get(f"/api/rooms/1/available-dates?month={month}")
        assert r.status_code == 400 and code(r) == "INVALID_MONTH", month
    assert client.get("/api/rooms/1/available-dates?month=2026-13").status_code == 400


# ---- 이중 예약 DB 제약 위반(23P01) → 409 ROOM_NOT_AVAILABLE (#60 4번-②) ----
# 제약은 ③단계에서 DB 담당이 건다. 지금은 commit 이 PostgreSQL 과 같은 오류를 내게 해서 바꾸는 코드만 확인한다.

import psycopg  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402


def fail_commit_with(monkeypatch, pg_error):
    def commit(self):
        raise IntegrityError("INSERT INTO reservation ...", {}, pg_error)
    monkeypatch.setattr(Session, "commit", commit)


def test_overlap_constraint_violation_is_room_not_available(client, monkeypatch):
    fail_commit_with(monkeypatch, psycopg.errors.ExclusionViolation())  # SQLSTATE 23P01
    r = reserve(client, D1)
    assert r.status_code == 409 and code(r) == "ROOM_NOT_AVAILABLE"
    assert r.json()["detail"]["message"] == "선택한 날짜에 이미 예약이 있습니다."


def test_other_integrity_errors_are_not_hidden(client, monkeypatch):
    fail_commit_with(monkeypatch, psycopg.errors.CheckViolation())  # 23514: 겹침이 아니면 그대로 오류
    with pytest.raises(IntegrityError):
        reserve(client, D1)


# ---- 예약 때의 1박 요금 저장 · 응답 (#60 4번-①, 4-A3) ----

def test_reservation_saves_price_per_night(client):
    r = reserve(client, D1, nights=3, room_id=3)  # 201호 120000원
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["pricePerNight"] == 120000
    assert body["totalPrice"] == body["pricePerNight"] * 3

    rid = body["reservationId"]
    assert client.get(f"{API}/{rid}", headers=GUEST).json()["pricePerNight"] == 120000  # 완료 화면
    mine = {x["reservationId"]: x for x in client.get(f"{API}/me", headers=GUEST).json()}
    assert mine[rid]["pricePerNight"] == 120000  # 내 예약

    q = quote(client, D1, nights=3, room_id=3).json()  # 견적과 같은 값
    assert (q["pricePerNight"], q["totalPrice"]) == (body["pricePerNight"], body["totalPrice"])


def test_price_per_night_may_be_empty_for_old_rows():
    """③단계 전에는 비어 있는 옛 예약이 있을 수 있다(R5) → 응답은 null, 화면은 총액만."""
    from datetime import datetime

    from app.schemas.reservation import ReservationOut
    out = ReservationOut(
        reservation_id=1, member_id=2, room_id=1, check_in_date=D1, check_out_date=D1 + timedelta(days=1),
        guest_count=1, total_price=80000, price_per_night=None, status="PENDING", request_memo=None,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    assert out.model_dump(by_alias=True)["pricePerNight"] is None
