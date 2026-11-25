"""휴무일(ADM-002): 시드 1번 = ADMIN, 2번 = USER. 쿠키는 로그인 대신 같은 방식으로 직접 만든다."""
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
ADMIN = {"Cookie": f"{COOKIE}={create_session_token(1, SEED_PASSWORD)}"}
GUEST = {"Cookie": f"{COOKIE}={create_session_token(2, SEED_PASSWORD)}"}
API = "/api/admin/closed-dates"
TODAY = today_kst()
# 시드(2026-12 예약)와 겹치지 않고, 예약 가능 범위(오늘부터 365일, reservation_service.BOOKING_WINDOW_DAYS) 안인 미래 날짜
D1 = max(TODAY + timedelta(days=30), date(2027, 1, 4))


def add_reservation(room_id, check_in, nights, status="PENDING"):
    helpers.add_reservation(room_id, check_in, nights, status, total_price=80000)


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
    assert post(client, TODAY).status_code == 201
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
    assert post_range(client, D1 + timedelta(days=90), D1 + timedelta(days=91), room_id=999).status_code == 404


def recommended_ids(client, check_in, nights=1):
    q = f"checkIn={check_in}&checkOut={check_in + timedelta(days=nights)}&size=50"
    return {r["roomId"] for r in client.get(f"/api/rooms/recommend?{q}").json()["items"]}


def reserve(client, room_id, check_in, nights=1):
    body = {"roomId": room_id, "checkInDate": check_in.isoformat(),
            "checkOutDate": (check_in + timedelta(days=nights)).isoformat(), "guestCount": 1}
    return client.post("/api/reservations", json=body, headers=GUEST)


def test_closed_dates_block_recommend_and_reservation(client):
    """3C: 휴무가 객실 추천 · 예약에서 실제로 막히는지 (다른 파트가 같이 쓰는 available_room_filter)."""
    all_rooms = recommended_ids(client, D1)
    assert {1, 2} <= all_rooms

    # 객실 판매 중지: 그 방만 빠지고 예약도 거부
    assert post_range(client, D1, D1 + timedelta(days=1), room_id=1).status_code == 201
    assert recommended_ids(client, D1) == all_rooms - {1}
    assert reserve(client, 1, D1).json()["detail"]["code"] == "ROOM_CLOSED"  # 설계서 4-13: 판매 중지
    assert reserve(client, 2, D1).status_code == 201

    # 호텔 전체 휴무: 기간에 하루라도 걸리면 모든 방이 빠진다
    assert post(client, D1 + timedelta(days=5)).status_code == 201
    assert recommended_ids(client, D1 + timedelta(days=4), nights=2) == set()
    r = reserve(client, 3, D1 + timedelta(days=4), nights=2)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "DATE_CLOSED"  # 설계서 4-13: 호텔 전체 휴무

    # 휴무일이 체크아웃 날이면 묵지 않으므로 예약 가능
    assert 3 in recommended_ids(client, D1 + timedelta(days=4))
    assert reserve(client, 3, D1 + timedelta(days=4)).status_code == 201


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


def delete_range(client, start, end, room_id=None, headers=ADMIN):
    q = f"startDate={start}&endDate={end}" + (f"&roomId={room_id}" if room_id else "")
    return client.delete(f"{API}/range?{q}", headers=headers)


def test_past_dates_can_be_closed_and_released(client):
    """#32 팀 결정: 지난 날짜도 지정 · 해제 가능."""
    past = TODAY - timedelta(days=30)
    r = post(client, past)
    assert r.status_code == 201, r.text
    assert client.delete(f"{API}/{r.json()['closedDateId']}", headers=ADMIN).status_code == 204
    assert post_range(client, past, past + timedelta(days=2), room_id=2).status_code == 201
    assert delete_range(client, past, past + timedelta(days=2), room_id=2).json() == {"deleted": 3}

    # 그날 손님이 묵었으면(대기 · 승인) 지난 날짜라도 휴무로 지정할 수 없다. 취소된 예약은 막지 않는다
    add_reservation(room_id=1, check_in=past, nights=2, status="APPROVED")
    add_reservation(room_id=3, check_in=past, nights=1, status="CANCELED")
    assert post(client, past + timedelta(days=1), room_id=1).json()["detail"]["code"] == "CLOSED_DATE_CONFLICT"
    assert post(client, past).json()["detail"]["code"] == "CLOSED_DATE_CONFLICT"  # 호텔 전체도 불가
    assert post_range(client, past - timedelta(days=1), past + timedelta(days=1), room_id=1).status_code == 409
    assert post(client, past, room_id=3).status_code == 201
    assert post(client, past + timedelta(days=2), room_id=1).status_code == 201  # 체크아웃 날


def test_range_release_only_same_scope(client):
    """#28: 기간 해제는 한 번에, 다른 범위(호텔 전체 ↔ 방)는 건드리지 않음."""
    assert post_range(client, D1, D1 + timedelta(days=4)).status_code == 201  # 호텔 전체 5일
    assert post(client, D1 + timedelta(days=6), room_id=1).status_code == 201  # 101호 하루

    assert delete_range(client, D1, D1 + timedelta(days=10), room_id=2).status_code == 404  # 102호는 없음
    assert delete_range(client, D1, D1 + timedelta(days=10)).json() == {"deleted": 5}
    left = client.get(f"{API}?month={D1:%Y-%m}", headers=ADMIN).json()
    left += client.get(f"{API}?month={D1 + timedelta(days=6):%Y-%m}", headers=ADMIN).json()
    assert {(c["closedDate"], c["roomId"]) for c in left} == {((D1 + timedelta(days=6)).isoformat(), 1)}

    assert delete_range(client, D1 + timedelta(days=5), D1).status_code == 400
    assert delete_range(client, D1, D1, headers=GUEST).status_code == 403
    assert delete_range(client, D1, D1, headers={}).status_code == 401


def test_range_reports_all_blocked_dates(client):
    """#29: 막힌 날짜를 한 번에 모두 알려 주고, 아무것도 넣지 않음."""
    add_reservation(room_id=1, check_in=D1 + timedelta(days=1), nights=1)
    add_reservation(room_id=2, check_in=D1 + timedelta(days=3), nights=1)
    assert post(client, D1 + timedelta(days=5)).status_code == 201

    r = post_range(client, D1, D1 + timedelta(days=6))
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["code"] == "CLOSED_DATE_CONFLICT"
    assert [b["date"] for b in detail["blockedDates"]] == [
        (D1 + timedelta(days=i)).isoformat() for i in (1, 3, 5)]
    assert [b["code"] for b in detail["blockedDates"]] == ["CLOSED_DATE_CONFLICT"] * 2 + ["ALREADY_CLOSED"]
    assert "이미 휴무입니다" in detail["message"] and "예약이 있습니다" in detail["message"]
    months = {f"{D1 + timedelta(days=i):%Y-%m}" for i in range(7)}  # 기간이 달을 넘을 수 있음
    rows = [c for m in sorted(months) for c in client.get(f"{API}?month={m}", headers=ADMIN).json()]
    assert [c["closedDate"] for c in rows] == [(D1 + timedelta(days=5)).isoformat()]  # 기존 1건만


def test_day_list_format():
    from app.api.routes.admin.closed_dates import day_list
    assert day_list([date(2026, 12, 15), date(2026, 12, 17), date(2027, 1, 2)]) == "12월 15일 · 17일 · 1월 2일"


def test_available_rooms_ignores_inactive_rooms(client):
    """#30: 남은 객실 = 사용 중 객실 − 휴무 객실 − 숙박 중 객실, 비활성 객실 예약은 영향 없음."""
    month = f"{D1:%Y-%m}"

    def left(day):
        return client.get(f"{API}/available-rooms?month={day:%Y-%m}", headers=ADMIN).json()[day.isoformat()]

    total = left(D1)
    assert total > 2
    add_reservation(room_id=1, check_in=D1, nights=1)
    assert left(D1) == total - 1
    assert post(client, D1, room_id=2).status_code == 201
    assert left(D1) == total - 2

    with engine.begin() as conn:  # 101호를 비활성으로 → 그 예약은 남은 수에 영향 없음
        conn.execute(text("UPDATE room SET is_active = 'N' WHERE room_id = 1"))
    assert left(D1) == total - 2  # 사용 중 객실이 1 줄고, 101호 예약은 세지 않음

    assert post(client, D1 + timedelta(days=1)).status_code == 201
    assert left(D1 + timedelta(days=1)) == 0  # 호텔 전체 휴무
    assert len(client.get(f"{API}/available-rooms?month={month}", headers=ADMIN).json()) >= 28
