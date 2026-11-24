"""객실 추천(ROOM-001): GET /api/rooms/recommend, POST /api/rooms/{id}/view. 빈 DB에 방·예약을 직접 넣는다."""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.dates import today_kst
from app.db.session import engine
from app.services import room_service

pytestmark = pytest.mark.usefixtures("empty_db")

API = "/api/rooms/recommend"
TODAY = today_kst()
FUTURE = TODAY + timedelta(days=400)


def run(sql, **params):
    with engine.begin() as conn:
        result = conn.execute(text(sql), params)
        return result.scalar() if result.returns_rows else None


@pytest.fixture(autouse=True)
def guest(empty_db):
    run("INSERT INTO member (login_id, password, name) VALUES ('guest1', 'x', '손님')")


def room(name, views=0, price=100000, max_guest=2, active="Y"):
    return run("INSERT INTO room (room_name, room_type, max_guest, price, view_count, is_active)"
               " VALUES (:name, 'STANDARD', :guest, :price, :views, :active) RETURNING room_id",
               name=name, guest=max_guest, price=price, views=views, active=active)


def book(room_id, check_in=FUTURE, nights=1, status="APPROVED", created=None):
    run("INSERT INTO reservation (member_id, room_id, check_in_date, check_out_date, guest_count, total_price,"
        " status, created_at) VALUES (1, :room, :cin, :cout, 1, 1, :status, :created)",
        room=room_id, cin=check_in, cout=check_in + timedelta(days=nights), status=status,
        created=created or datetime.now())


def get(client, **query):
    r = client.get(API, params=query)
    assert r.status_code == 200, r.text
    return r.json()


def names(body):
    return [i["roomName"] for i in body["items"]]


def stay(start, nights):
    return {"checkIn": str(start), "checkOut": str(start + timedelta(days=nights))}


# ---------- 점수 · 정렬 ----------

def test_score_is_ratio_to_max_times_30_plus_70(client):
    room("조회만 많은 방", views=100)            # 100/100*30 + 0      = 30
    busy = room("예약 많은 방", views=10)        # 10/100*30 + 4/4*70  = 73
    for i in range(4):
        book(busy, FUTURE + timedelta(days=i * 2))
    room("아무것도 없는 방")                      # 0

    body = get(client)
    assert names(body) == ["예약 많은 방", "조회만 많은 방", "아무것도 없는 방"]
    assert [i["score"] for i in body["items"]] == [73.0, 30.0, 0.0]
    assert [i["isRecommended"] for i in body["items"]] == [True, False, False]
    assert body["items"][0]["recentReservations"] == 4
    assert (body["total"], body["page"], body["size"]) == (3, 1, 6)


def test_many_views_do_not_beat_many_bookings(client):
    # 그냥 곱하면 200*0.3+1*0.7=60.7 이 120*0.3+5*0.7=39.5 를 이긴다
    city = room("시티뷰", views=200)
    ocean = room("오션뷰", views=120)
    book(city)
    for i in range(5):
        book(ocean, FUTURE + timedelta(days=i * 2))
    assert [(i["roomName"], i["score"]) for i in get(client)["items"]] == [("오션뷰", 88.0), ("시티뷰", 44.0)]


def test_counts_pending_not_canceled_and_recent_is_30_days(client):
    a = room("A")
    book(a, status="CANCELED")
    book(a, FUTURE + timedelta(days=3), status="PENDING")
    book(a, FUTURE + timedelta(days=6), created=datetime.now() - timedelta(days=room_service.RECENT_DAYS + 1))
    item = get(client)["items"][0]
    assert (item["recentReservations"], item["totalReservations"]) == (1, 2)


def test_three_sorts_differ_and_badge_only_on_recommend_first(client):
    hot = room("최근 인기", views=50, price=200000)
    old = room("예전 인기", views=10, price=150000)
    room("제일 싼 방", price=50000)
    book(hot)
    long_ago = datetime.now() - timedelta(days=60)
    for i in range(3):
        book(old, FUTURE + timedelta(days=10 + i * 2), created=long_ago)

    recommend = get(client, sort="recommend")
    assert names(recommend) == ["최근 인기", "예전 인기", "제일 싼 방"]
    assert [i["isRecommended"] for i in recommend["items"]] == [True, False, False]
    assert names(get(client, sort="popular")) == ["예전 인기", "최근 인기", "제일 싼 방"]
    cheap = get(client, sort="price")
    assert names(cheap) == ["제일 싼 방", "예전 인기", "최근 인기"]
    assert not any(i["isRecommended"] for i in cheap["items"])


def test_no_badge_when_everyone_scores_zero(client):
    room("A")
    room("B")
    assert not any(i["isRecommended"] for i in get(client)["items"])


def test_max_is_taken_from_all_active_rooms_not_search_result(client):
    room("큰 방", views=100, max_guest=6)
    room("작은 방", views=50, max_guest=2)
    assert [(i["roomName"], i["score"]) for i in get(client, guests=3)["items"]] == [("큰 방", 30.0)]
    assert {i["roomName"]: i["score"] for i in get(client, guests=1)["items"]}["작은 방"] == 15.0


# ---------- 걸러내기 ----------

def test_inactive_room_is_hidden_and_not_in_max(client):
    room("내린 방", views=1000, active="N")
    room("판매 방", views=10)
    body = get(client)
    assert names(body) == ["판매 방"] and body["items"][0]["score"] == 30.0


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
    run("INSERT INTO closed_date (room_id, closed_date, reason) VALUES (:room, :day, '점검')", room=a, day=FUTURE)
    assert names(get(client, **stay(FUTURE, 2))) == ["B"]
    run("INSERT INTO closed_date (room_id, closed_date, reason) VALUES (NULL, :day, '전체 휴무')",
        day=FUTURE + timedelta(days=1))
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
    assert get(client)["items"][0]["viewCount"] == 2
    for room_id in (hidden, 999999):
        r = client.post(f"/api/rooms/{room_id}/view")
        assert r.status_code == 404 and r.json()["detail"]["code"] == "ROOM_NOT_FOUND"
