"""객실 추천(ROOM-001): GET /api/rooms/recommend, POST /api/rooms/{id}/view. 빈 DB에 방·예약을 직접 넣는다."""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.dates import today_kst
from app.db.session import engine
from app.services import room_service
from tests import helpers

pytestmark = pytest.mark.usefixtures("empty_db")

API = "/api/rooms/recommend"
TODAY = today_kst()
FUTURE = TODAY + timedelta(days=10)  # 예약 가능 범위(오늘부터 30일, reservation_service.BOOKING_WINDOW_DAYS) 안


def run(sql, **params):
    with engine.begin() as conn:
        result = conn.execute(text(sql), params)
        return result.scalar() if result.returns_rows else None


@pytest.fixture(autouse=True)
def guest(empty_db):
    run("INSERT INTO member (login_id, password, name) VALUES ('guest1', 'x', '손님')")


OLD = datetime.now() - timedelta(days=room_service.NEW_DAYS + 1)  # NEW 뱃지가 안 붙는 등록일


def room(name, views=0, price=100000, max_guest=2, active="Y", created=OLD):
    return run("INSERT INTO room (room_name, room_type, max_guest, price, view_count, is_active, created_at)"
               " VALUES (:name, 'STANDARD', :guest, :price, :views, :active, :created) RETURNING room_id",
               name=name, guest=max_guest, price=price, views=views, active=active, created=created)


def book(room_id, check_in=FUTURE, nights=1, status="APPROVED", created=None):
    helpers.add_reservation(room_id, check_in, nights, status, member_id=1, price_per_night=1,
                            total_price=1, created_at=created)


def get(client, **query):
    r = client.get(API, params=query)
    assert r.status_code == 200, r.text
    return r.json()


def names(body):
    return [i["roomName"] for i in body["items"]]


def stay(start, nights):
    return {"checkIn": str(start), "checkOut": str(start + timedelta(days=nights))}


# ---------- 점수 · 정렬 ----------

def test_score_is_ratio_to_max_times_40_plus_60(client):
    room("조회만 많은 방", views=100)            # 100/100*40 + 0      = 40
    busy = room("예약 많은 방", views=10)        # 10/100*40 + 4/4*60  = 64
    for i in range(4):
        book(busy, FUTURE + timedelta(days=i * 2))
    room("아무것도 없는 방")                      # 0

    body = get(client)
    assert names(body) == ["예약 많은 방", "조회만 많은 방", "아무것도 없는 방"]
    assert [i["score"] for i in body["items"]] == [64.0, 40.0, 0.0]
    assert [i["isRecommended"] for i in body["items"]] == [True, True, False]  # 1~3위지만 0점은 아님
    assert body["items"][0]["recentReservations"] == 4
    assert (body["total"], body["page"], body["size"]) == (3, 1, 6)


def test_many_views_do_not_beat_many_bookings(client):
    # 그냥 곱하면 200*0.4+1*0.6=80.6 이 120*0.4+5*0.6=51 을 이긴다
    city = room("시티뷰", views=200)
    ocean = room("오션뷰", views=120)
    book(city)
    for i in range(5):
        book(ocean, FUTURE + timedelta(days=i * 2))
    assert [(i["roomName"], i["score"]) for i in get(client)["items"]] == [("오션뷰", 84.0), ("시티뷰", 52.0)]


def test_counts_only_approved_and_recent_is_30_days(client):
    a = room("A")
    book(a, status="CANCELED")
    book(a, FUTURE + timedelta(days=3), status="PENDING")  # 대기는 취소될 수 있어서 세지 않는다
    book(a, FUTURE + timedelta(days=6))
    book(a, FUTURE + timedelta(days=9), created=datetime.now() - timedelta(days=room_service.RECENT_DAYS + 1))
    item = get(client)["items"][0]
    assert (item["recentReservations"], item["totalReservations"]) == (1, 2)


def test_pending_counts_after_approval(client):
    a, b = room("A", views=10), room("B", views=5)
    book(b, status="PENDING")
    assert names(get(client)) == ["A", "B"]
    run("UPDATE reservation SET status = 'APPROVED'")
    assert names(get(client)) == ["B", "A"]  # 승인되면 순위에 반영


def test_three_sorts_differ_and_badge_follows_room_not_sort(client):
    hot = room("최근 인기", views=50, price=200000)
    old = room("예전 인기", views=10, price=150000)
    room("제일 싼 방", price=50000)
    book(hot)
    long_ago = datetime.now() - timedelta(days=60)
    for i in range(3):
        book(old, FUTURE + timedelta(days=10 + i * 2), created=long_ago)

    recommend = get(client, sort="recommend")
    assert names(recommend) == ["최근 인기", "예전 인기", "제일 싼 방"]
    assert [i["isRecommended"] for i in recommend["items"]] == [True, True, False]
    assert names(get(client, sort="popular")) == ["예전 인기", "최근 인기", "제일 싼 방"]
    cheap = get(client, sort="price")
    assert names(cheap) == ["제일 싼 방", "예전 인기", "최근 인기"]
    assert [i["isRecommended"] for i in cheap["items"]] == [False, True, True]


def test_no_badge_when_everyone_scores_zero(client):
    room("A")
    room("B")
    assert not any(i["isRecommended"] for i in get(client)["items"])


def test_max_is_taken_from_all_active_rooms_not_search_result(client):
    room("큰 방", views=100, max_guest=6)
    room("작은 방", views=50, max_guest=2)
    assert [(i["roomName"], i["score"]) for i in get(client, guests=3)["items"]] == [("큰 방", 40.0)]
    assert {i["roomName"]: i["score"] for i in get(client, guests=1)["items"]}["작은 방"] == 20.0


# ---------- 뱃지 (BEST > HOT > NEW, 하나만) ----------

def badges(client, **query):
    return {i["roomName"]: i["badge"] for i in get(client, size=50, **query)["items"]}


def test_best_is_top3_score_even_when_search_hides_others(client):
    for n in range(5):
        room(f"방{n}", views=n * 10, max_guest=2 + n)   # 방4 > 방3 > 방2 > 방1 > 방0(0점)
    assert badges(client) == {"방4": "BEST", "방3": "BEST", "방2": "BEST", "방1": None, "방0": None}
    # 4명 검색이면 방2~4만 나오지만 순위는 전체 기준이라 그대로 BEST
    assert badges(client, guests=4) == {"방4": "BEST", "방3": "BEST", "방2": "BEST"}
    assert badges(client, sort="price")["방4"] == "BEST"


def test_hot_is_top3_approved_bookings_in_7_days(client):
    ten_days_ago = datetime.now() - timedelta(days=10)  # 30일 안(점수에 들어감)이지만 7일 밖
    for n, views in ((5, 30), (4, 20), (3, 10)):       # 점수 1~3위: 10일 전 예약 3건씩
        rid = room(f"방{n}", views=views)
        for i in range(3):
            book(rid, FUTURE + timedelta(days=i * 2), created=ten_days_ago)
    for n in (2, 1):                                     # 오늘 예약 1건씩 → 점수는 낮지만 7일 안
        book(room(f"방{n}"), FUTURE + timedelta(days=20))
    book(room("방0"), FUTURE + timedelta(days=30), status="PENDING")  # 대기는 HOT 에도 안 센다
    assert badges(client) == {"방5": "BEST", "방4": "BEST", "방3": "BEST", "방2": "HOT", "방1": "HOT", "방0": None}


def test_new_is_registered_within_14_days(client):
    room("오래된 방")
    room("새 방", created=datetime.now() - timedelta(days=room_service.NEW_DAYS - 1))
    assert badges(client) == {"오래된 방": None, "새 방": "NEW"}


def test_best_wins_over_new(client):
    room("새 인기 방", views=10, created=datetime.now())
    assert badges(client) == {"새 인기 방": "BEST"}


# ---------- 걸러내기 ----------

def test_inactive_room_is_hidden_and_not_in_max(client):
    room("내린 방", views=1000, active="N")
    room("판매 방", views=10)
    body = get(client)
    assert names(body) == ["판매 방"] and body["items"][0]["score"] == 40.0


def test_overlapping_booking_hides_room_but_checkout_day_is_free(client):
    booked = room("예약된 방")
    room("빈 방")
    book(booked, FUTURE, nights=2)                                  # FUTURE, +1 숙박
    assert names(get(client, **stay(FUTURE + timedelta(days=1), 2))) == ["빈 방"]
    assert sorted(names(get(client, **stay(FUTURE + timedelta(days=2), 1)))) == ["빈 방", "예약된 방"]


def test_canceled_booking_does_not_block(client):
    a = room("A")
    book(a, status="CANCELED")
    assert names(get(client, **stay(FUTURE, 1))) == ["A"]


def test_room_and_hotel_closed_dates_hide_rooms(client):
    a = room("A")
    room("B")
    helpers.add_closed_date(FUTURE, a, "점검")
    assert names(get(client, **stay(FUTURE, 2))) == ["B"]
    helpers.add_closed_date(FUTURE + timedelta(days=1), None, "전체 휴무")
    assert get(client, **stay(FUTURE, 2))["total"] == 0
    # 휴무일이 체크아웃 날이면 묵지 않으므로 괜찮다
    assert sorted(names(get(client, **stay(FUTURE - timedelta(days=1), 1)))) == ["A", "B"]


def test_rooms_smaller_than_guests_are_hidden(client):
    room("2인실", max_guest=2)
    room("4인실", max_guest=4)
    assert names(get(client, guests=3)) == ["4인실"]


def test_six_per_page(client):
    for n in range(8):
        room(f"방{n}", views=n)
    first, second = get(client), get(client, page=2)
    assert len(first["items"]) == 6 and len(second["items"]) == 2
    assert first["total"] == second["total"] == 8
    assert not set(names(first)) & set(names(second))
    assert not any(i["isRecommended"] for i in second["items"])


@pytest.mark.parametrize("query", [
    {"checkIn": str(FUTURE)},
    stay(TODAY - timedelta(days=1), 1),
    {"checkIn": str(FUTURE), "checkOut": str(FUTURE)},
])
def test_bad_dates_are_400(client, query):
    r = client.get(API, params=query)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "INVALID_DATES"


def test_stay_range_follows_reservation_rule(client):
    """#77: 예약과 같은 제한 — 최대 MAX_NIGHTS 박, 체크인은 오늘부터 BOOKING_WINDOW_DAYS 일 안"""
    from app.services.reservation_service import BOOKING_WINDOW_DAYS, MAX_NIGHTS

    room("A")
    assert names(get(client, **stay(TODAY, MAX_NIGHTS))) == ["A"]
    assert names(get(client, **stay(TODAY + timedelta(days=BOOKING_WINDOW_DAYS), 1))) == ["A"]
    for query, code in [
        (stay(TODAY, MAX_NIGHTS + 1), "TOO_LONG_STAY"),
        (stay(TODAY + timedelta(days=BOOKING_WINDOW_DAYS + 1), 1), "TOO_FAR_DATE"),
    ]:
        r = client.get(API, params=query)
        assert r.status_code == 400 and r.json()["detail"]["code"] == code, r.text


def test_today_check_in_is_allowed(client):
    room("A")
    assert names(get(client, **stay(TODAY, 1))) == ["A"]


def test_thumbnail_is_first_room_file(client):
    a = room("A")
    for name in ("first.jpg", "second.jpg"):
        run("INSERT INTO attach_file (target_type, target_id, original_name, saved_path, file_size)"
            " VALUES ('ROOM', :id, :name, :path, 1)", id=a, name=name, path=f"uploads/rooms/{name}")
    room("사진 없는 방")
    photos = {i["roomName"]: i["thumbnailUrl"] for i in get(client)["items"]}
    assert photos == {"A": "uploads/rooms/first.jpg", "사진 없는 방": None}


# ---------- 조회수 ----------

def test_view_count_without_login_and_404_for_hidden_or_missing(client):
    a = room("A")
    hidden = room("B", active="N")
    assert client.post(f"/api/rooms/{a}/view").status_code == 204
    assert client.post(f"/api/rooms/{a}/view").status_code == 204
    assert get(client)["items"][0]["viewCount"] == 1  # 같은 손님 · 같은 날은 1번(1-A1, test_room_view.py)
    for room_id in (hidden, 999999):
        r = client.post(f"/api/rooms/{room_id}/view")
        assert r.status_code == 404 and r.json()["detail"]["code"] == "ROOM_NOT_FOUND"


# ---------- 객실 상세 (1B) ----------

def test_detail_has_photos_badge_and_counts(client):
    a = room("A", views=10)
    book(a)
    room("B")
    for name in ("first.jpg", "second.jpg"):
        run("INSERT INTO attach_file (target_type, target_id, original_name, saved_path, file_size)"
            " VALUES ('ROOM', :id, :name, :path, 1)", id=a, name=name, path=f"uploads/rooms/{name}")
    r = client.get(f"/api/rooms/{a}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["photos"] == ["uploads/rooms/first.jpg", "uploads/rooms/second.jpg"]
    assert body["thumbnailUrl"] == "uploads/rooms/first.jpg"
    assert (body["badge"], body["isRecommended"], body["score"]) == ("BEST", True, 100.0)
    assert (body["recentReservations"], body["totalReservations"]) == (1, 1)
    # 목록과 같은 뱃지
    assert {i["roomName"]: i["badge"] for i in get(client)["items"]}["A"] == body["badge"]


def test_detail_404_for_hidden_or_missing(client):
    hidden = room("숨김", active="N")
    for room_id in (hidden, 999999):
        r = client.get(f"/api/rooms/{room_id}")
        assert r.status_code == 404 and r.json()["detail"]["code"] == "ROOM_NOT_FOUND"
