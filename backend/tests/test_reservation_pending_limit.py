"""#68 회원 한 명의 승인 대기(PENDING) 예약 상한 — 가짜 대기 예약으로 객실을 전부 막지 못하게.

시드 1번 회원(관리자 자리, 예약 없음)으로 예약해서 0건에서 시작한다. 2번(guest1)은 시드 대기 예약이 1건 있다.
예약 행은 tests/helpers.py 도우미로만 넣는다(#60 R2).
"""
from datetime import date, timedelta

import pytest

from app.core.config import get_settings
from app.core.dates import today_kst
from app.core.security import create_session_token
from app.services.reservation_service import MAX_PENDING_PER_MEMBER
from tests import helpers

pytestmark = pytest.mark.usefixtures("seeded_db")

SEED_PASSWORD = "not-a-real-hash"
COOKIE = get_settings().session_cookie
MEMBER1 = {"Cookie": f"{COOKIE}={create_session_token(1, SEED_PASSWORD)}"}
ADMIN = MEMBER1  # 시드 1번은 ADMIN 이라 관리자 취소에도 쓴다
TODAY = today_kst()
D1 = max(TODAY + timedelta(days=30), date(2027, 1, 4))  # 시드(2026-12)와 겹치지 않고 예약 가능 범위 안


def reserve(client, check_in, room_id=1, nights=2, headers=MEMBER1):
    body = {"roomId": room_id, "checkInDate": check_in.isoformat(),
            "checkOutDate": (check_in + timedelta(days=nights)).isoformat(), "guestCount": 1}
    return client.post("/api/reservations", json=body, headers=headers)


def fill_to_limit(client):
    """서로 겹치지 않는 날짜로 상한만큼 대기 예약을 만든다."""
    ids = []
    for i in range(MAX_PENDING_PER_MEMBER):
        r = reserve(client, D1 + timedelta(days=3 * i))
        assert r.status_code == 201, r.text
        ids.append(r.json()["reservationId"])
    return ids


def test_pending_limit(client):
    fill_to_limit(client)
    r = reserve(client, D1 + timedelta(days=20))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "TOO_MANY_PENDING"
    assert f"최대 {MAX_PENDING_PER_MEMBER}건" in r.json()["detail"]["message"]
    r = reserve(client, D1 + timedelta(days=20), room_id=2)  # 다른 방이어도 막힘
    assert r.json()["detail"]["code"] == "TOO_MANY_PENDING"


def test_cancel_or_approve_frees_a_slot(client):
    first, second, _ = fill_to_limit(client)
    assert client.patch(f"/api/admin/reservations/{first}/cancel", headers=ADMIN).status_code == 200
    assert reserve(client, D1 + timedelta(days=20)).status_code == 201  # 취소하면 한 자리
    assert client.patch(f"/api/admin/reservations/{second}/approve", headers=ADMIN).status_code == 200
    assert reserve(client, D1 + timedelta(days=25)).status_code == 201  # 승인돼도 한 자리 (대기만 셈)
    assert reserve(client, D1 + timedelta(days=30)).json()["detail"]["code"] == "TOO_MANY_PENDING"


def test_only_live_future_pending_counts(client):
    # 승인 · 취소 예약, 이미 끝난 대기 예약, 다른 회원의 대기 예약은 세지 않는다
    helpers.add_reservation(1, D1 + timedelta(days=40), status="APPROVED", member_id=1)
    helpers.add_reservation(1, D1 + timedelta(days=42), status="CANCELED", member_id=1)
    helpers.add_reservation(2, TODAY - timedelta(days=5), nights=2, status="PENDING", member_id=1)  # 지난 대기
    for i in range(MAX_PENDING_PER_MEMBER):
        helpers.add_reservation(3, D1 + timedelta(days=3 * i), status="PENDING", member_id=2)  # 다른 회원
    fill_to_limit(client)  # 1번 회원은 여전히 상한만큼 만들 수 있음


def test_seed_guest_already_has_one_pending(client):
    """시드 2번(guest1)은 대기 예약 1건(2026-12-24)이 있어서 상한 - 1 건만 더 만들 수 있다."""
    if TODAY >= date(2026, 12, 26):
        pytest.skip("시드 대기 예약이 이미 끝남")
    guest = {"Cookie": f"{COOKIE}={create_session_token(2, SEED_PASSWORD)}"}
    for i in range(MAX_PENDING_PER_MEMBER - 1):
        assert reserve(client, D1 + timedelta(days=3 * i), headers=guest).status_code == 201
    assert reserve(client, D1 + timedelta(days=20), headers=guest).json()["detail"]["code"] == "TOO_MANY_PENDING"
