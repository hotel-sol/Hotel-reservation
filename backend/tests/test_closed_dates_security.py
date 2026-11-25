"""3번 보안 점검(#66) — 휴무일 API 입력 경계 · 동시성."""
import threading
from datetime import timedelta

import pytest

from app.db.session import SessionLocal
from tests.test_closed_dates import ADMIN, API, D1, post

pytestmark = pytest.mark.usefixtures("seeded_db")


def test_month_year_out_of_range_is_400_not_500(client):
    for month in ("0000-01", "1999-12", "2101-01"):
        for path in ("", "/reservation-counts", "/available-rooms"):
            r = client.get(f"{API}{path}?month={month}", headers=ADMIN)
            assert r.status_code == 400 and r.json()["detail"]["code"] == "INVALID_MONTH", (path, month)
        assert client.get(f"/api/admin/closures?month={month}", headers=ADMIN).status_code == 400


def test_long_detail_reason_is_rejected_not_500(client):
    r = client.post(API, json={"closedDate": D1.isoformat(), "reasonCode": "MAINTENANCE", "reason": "가" * 200},
                    headers=ADMIN)
    assert r.status_code == 422
    r = client.post(API, json={"closedDate": D1.isoformat(), "reasonCode": "MAINTENANCE", "reason": "가" * 190},
                    headers=ADMIN)
    assert r.status_code == 201 and r.json()["reason"] == "점검 · " + "가" * 190


def test_range_release_is_limited(client):
    r = client.delete(f"{API}/range?startDate=2000-01-01&endDate=2100-12-31", headers=ADMIN)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "RANGE_TOO_LONG"


def test_closing_waits_for_reservation_holding_room_lock(client):
    """#66-1: 예약 저장이 객실 행을 잠그고 있으면 휴무 지정은 기다렸다가, 커밋된 예약을 보고 409."""
    from sqlalchemy import text

    from app.models import Room

    booking = SessionLocal()
    booking.get(Room, 1, with_for_update=True)  # 예약 저장 중인 것처럼 1번 방을 잠금
    result = {}
    t = threading.Thread(target=lambda: result.setdefault("r", post(client, D1, room_id=1)))
    t.start()
    t.join(1.5)
    assert t.is_alive()  # 잠금을 기다리는 중
    # 잠금을 쥔 같은 트랜잭션에서 넣어야 해서 helpers 대신 직접 INSERT (R2 예외)
    booking.execute(text("INSERT INTO reservation (member_id, room_id, check_in_date, check_out_date, guest_count,"
                         " total_price, status, price_per_night) VALUES (2, 1, :d, :d2, 1, 80000, 'PENDING', 80000)"),
                    {"d": D1, "d2": D1 + timedelta(days=1)})
    booking.commit()
    booking.close()
    t.join(10)
    assert result["r"].status_code == 409 and result["r"].json()["detail"]["code"] == "CLOSED_DATE_CONFLICT"
