"""관리자 예약 관리(ADM-003): 시드 1번 = ADMIN, 2번 = USER(손님1).

시드 예약: 1번 101호 12/15~18 APPROVED, 2번 201호 12/24~26 PENDING, 3번 102호 12/20~21 CANCELED.
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
API = "/api/admin/reservations"
TODAY = today_kst()


def add_reservation(check_in, status="PENDING", room_id=4):
    with engine.begin() as conn:
        return conn.execute(
            text("INSERT INTO reservation (member_id, room_id, check_in_date, check_out_date, guest_count,"
                 " total_price, status) VALUES (2, :room, :cin, :cout, 1, 160000, :status) RETURNING reservation_id"),
            {"room": room_id, "cin": check_in, "cout": check_in + timedelta(days=1), "status": status},
        ).scalar_one()


def ids(client, **params):
    r = client.get(API, params=params, headers=ADMIN)
    assert r.status_code == 200, r.text
    return [x["reservationId"] for x in r.json()["items"]]


def test_admin_only(client):
    assert client.get(API).status_code == 401
    assert client.get(API, headers=GUEST).status_code == 403
    assert client.get(f"{API}/counts", headers=GUEST).status_code == 403
    assert client.patch(f"{API}/2/approve", headers=GUEST).status_code == 403


def test_list_by_status_newest_first_with_names(client):
    assert ids(client) == [3, 2, 1]
    assert ids(client, status="PENDING") == [2]
    assert ids(client, status="APPROVED") == [1]
    assert ids(client, status="CANCELED") == [3]
    row = client.get(API, params={"status": "PENDING"}, headers=ADMIN).json()["items"][0]
    assert (row["memberName"], row["roomName"]) == ("손님1", "201호")


def test_search_by_check_in_period_name_and_number(client):
    assert ids(client, **{"from": "2026-12-20", "to": "2026-12-31"}) == [3, 2]
    assert ids(client, keyword="손님") == [3, 2, 1]
    assert ids(client, keyword="2") == [2]  # 숫자면 예약 번호로도 찾는다
    assert ids(client, keyword="없는사람") == []


def test_paging(client):
    new = [add_reservation(TODAY + timedelta(days=500 + i * 2)) for i in range(11)]
    body = client.get(API, params={"status": "PENDING", "size": 10, "page": 2}, headers=ADMIN).json()
    # 대기 12건(시드 1 + 새로 11) 중 2쪽 = 가장 오래된 2건
    assert body["total"] == 12
    assert [x["reservationId"] for x in body["items"]] == [new[0], 2]


def test_counts_follow_search(client):
    assert client.get(f"{API}/counts", headers=ADMIN).json() == {"ALL": 3, "PENDING": 1, "APPROVED": 1, "CANCELED": 1}
    only_late_dec = client.get(f"{API}/counts", params={"from": "2026-12-20"}, headers=ADMIN).json()
    assert only_late_dec == {"ALL": 2, "PENDING": 1, "APPROVED": 0, "CANCELED": 1}


def test_status_rules(client):
    rid = add_reservation(TODAY + timedelta(days=30))
    approved = client.patch(f"{API}/{rid}/approve", headers=ADMIN)
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    # 승인 → 다시 승인 불가, 승인 → 취소 가능, 취소 → 아무것도 불가
    again = client.patch(f"{API}/{rid}/approve", headers=ADMIN).json()["detail"]
    assert again["code"] == "INVALID_STATUS"
    assert again["message"] == "이미 승인 상태인 예약이라 승인할 수 없습니다."
    assert client.patch(f"{API}/{rid}/cancel", headers=ADMIN).json()["status"] == "CANCELED"
    for action in ("approve", "cancel"):
        r = client.patch(f"{API}/{rid}/{action}", headers=ADMIN)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "INVALID_STATUS"
    assert client.patch(f"{API}/999999/approve", headers=ADMIN).status_code == 404


def test_pending_can_be_canceled_directly(client):
    assert client.patch(f"{API}/2/cancel", headers=ADMIN).json()["status"] == "CANCELED"


def test_past_check_in_cannot_be_canceled_but_today_can(client):
    past = add_reservation(TODAY - timedelta(days=1), status="APPROVED")
    r = client.patch(f"{API}/{past}/cancel", headers=ADMIN)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "PAST_CHECK_IN"
    today = add_reservation(TODAY, status="APPROVED", room_id=5)
    assert client.patch(f"{API}/{today}/cancel", headers=ADMIN).status_code == 200


def test_updated_at_uses_same_clock_as_created_at(client):
    """updated_at 은 DB now() 로 남겨서 created_at 과 시간대가 같다(서버 PC 시간대와 섞이지 않음)."""
    rid = add_reservation(TODAY + timedelta(days=40))
    body = client.patch(f"{API}/{rid}/approve", headers=ADMIN).json()
    created, updated = body["createdAt"], body["updatedAt"]
    assert updated >= created
    with engine.connect() as conn:
        gap = conn.execute(
            text("SELECT EXTRACT(EPOCH FROM (updated_at - created_at)) FROM reservation WHERE reservation_id = :id"),
            {"id": rid},
        ).scalar_one()
    assert 0 <= gap < 600  # 같은 시계라면 몇 초 차이. 시간대가 섞이면 9시간(32400초) 차이가 난다
