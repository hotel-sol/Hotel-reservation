"""회원: 가입 · 로그인 · 잠금 · 내 정보 · 비밀번호 변경 · 탈퇴 · 비밀번호 찾기 · 관리자 만들기."""
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.dates import today_kst
from app.core.security import verify_password
from app.db import create_admin
from app.db.session import engine
from tests import helpers

pytestmark = pytest.mark.usefixtures("empty_db")
COOKIE = get_settings().session_cookie


def signup(client, login_id="guest01", password="password123", **extra):
    return client.post("/api/members/signup", json={"loginId": login_id, "password": password, "name": "손님", **extra})


def login(client, login_id="guest01", password="password123"):
    return client.post("/api/members/login", json={"loginId": login_id, "password": password})


def sql(statement, **params):
    with engine.begin() as conn:
        return conn.execute(text(statement), params).mappings().all() if statement.lstrip().upper().startswith(
            "SELECT") else conn.execute(text(statement), params)


def stored_password(login_id):
    return sql("SELECT password FROM member WHERE login_id = :id", id=login_id)[0]["password"]


def test_signup_login_me_logout(client):
    r = signup(client, email="a@example.com", phone="010-1234-5678")
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "USER"

    assert client.get("/api/members/me").status_code == 401
    r = login(client)
    assert r.status_code == 200 and r.json()["loginId"] == "guest01"
    assert client.get("/api/members/me").json()["role"] == "USER"

    assert client.post("/api/members/logout").status_code == 200
    client.cookies.clear()  # TestClient는 삭제 쿠키를 그대로 들고 있어서 직접 비운다
    assert client.get("/api/members/me").status_code == 401


def test_password_is_salted_hash_not_plain(client):
    signup(client, "user_a")
    signup(client, "user_b")  # 같은 비밀번호
    a, b = stored_password("user_a"), stored_password("user_b")
    assert "password123" not in a
    scheme, salt, digest = a.split("$")
    assert scheme == "scrypt" and len(salt) == 32 and len(digest) == 128
    assert a != b  # 소금이 달라서 같은 비밀번호도 저장값이 다르다
    assert verify_password("password123", a) and not verify_password("wrong-pass", a)


def test_signup_rules(client):
    assert signup(client).status_code == 201
    assert signup(client).json()["detail"]["code"] == "DUPLICATE_LOGIN_ID"
    assert signup(client, "other1", email="x@example.com").status_code == 201
    assert signup(client, "other2", email="x@example.com").json()["detail"]["code"] == "DUPLICATE_EMAIL"
    assert signup(client, "ab").status_code == 422  # 아이디 4자 미만
    assert signup(client, "short_pw", password="1234567").status_code == 422
    assert signup(client, "bad_mail", email="not-mail").json()["detail"]["code"] == "INVALID_EMAIL"
    r = client.post("/api/members/signup",
                    json={"loginId": "sneaky", "password": "password123", "name": "x", "role": "ADMIN"})
    assert r.json()["role"] == "USER"  # 가입으로 관리자가 될 수 없다


def test_wrong_password_and_forged_cookie(client):
    signup(client)
    assert login(client, password="wrong-pass").status_code == 401
    assert login(client, "nobody").json()["detail"]["message"] == "아이디 또는 비밀번호가 올바르지 않습니다."
    client.cookies.set(COOKIE, "forged.cookie.value")
    assert client.get("/api/members/me").status_code == 401


def test_admin_only_api_and_role_change_applies_at_once(client):
    signup(client)
    login(client)
    assert client.get("/api/admin/rooms").status_code == 403
    sql("UPDATE member SET role = 'ADMIN' WHERE login_id = 'guest01'")
    assert client.get("/api/admin/rooms").status_code == 200  # 역할은 요청마다 DB에서 읽는다


def test_login_locks_after_five_failures(client):
    signup(client)
    for _ in range(5):
        assert login(client, password="wrong-pass").status_code == 401
    assert login(client).status_code == 429  # 맞는 비밀번호여도 잠김
    from app.api.routes import members
    members._fails.clear()  # 10분 지난 것으로 치고
    assert login(client).status_code == 200


def test_update_profile(client):
    signup(client, email="a@example.com")
    signup(client, "other1", email="b@example.com")
    login(client)
    r = client.put("/api/members/me", json={"name": "새이름", "phone": "010-1111-2222", "email": "new@example.com"})
    assert r.status_code == 200 and r.json()["name"] == "새이름"
    assert client.get("/api/members/me").json()["email"] == "new@example.com"
    r = client.put("/api/members/me", json={"name": "새이름", "email": "b@example.com"})
    assert r.json()["detail"]["code"] == "DUPLICATE_EMAIL"
    assert client.put("/api/members/me", json={"name": "   "}).status_code == 400


def test_change_password_logs_out_other_devices(client):
    signup(client)
    login(client)
    old_cookie = client.cookies.get(COOKIE)
    r = client.put("/api/members/me/password", json={"currentPassword": "wrong-pass", "newPassword": "newpass123"})
    assert r.json()["detail"]["code"] == "WRONG_PASSWORD"
    r = client.put("/api/members/me/password", json={"currentPassword": "password123", "newPassword": "newpass123"})
    assert r.status_code == 204
    assert client.get("/api/members/me").status_code == 200  # 지금 기기는 새 쿠키로 계속 로그인
    client.cookies.clear()
    client.cookies.set(COOKIE, old_cookie)
    assert client.get("/api/members/me").status_code == 401  # 예전 쿠키(다른 기기)는 끊김
    client.cookies.clear()
    assert login(client, password="password123").status_code == 401
    assert login(client, password="newpass123").status_code == 200


def test_withdraw_keeps_reservation_rows(client):
    signup(client, email="a@example.com", phone="010-1234-5678")
    login(client)
    me = client.get("/api/members/me").json()
    sql("INSERT INTO room (room_name, room_type, max_guest, price) VALUES ('101호', 'STANDARD', 2, 80000)")
    helpers.add_reservation(1, today_kst() + timedelta(days=5), member_id=me["memberId"])
    r = client.post("/api/members/me/withdraw", json={"password": "password123"})
    assert r.json()["detail"]["code"] == "HAS_RESERVATION"  # 진행 중인 예약이 있으면 불가

    sql("UPDATE reservation SET status = 'CANCELED', canceled_at = now()")
    assert client.post("/api/members/me/withdraw", json={"password": "wrong-pass"}).status_code == 400
    assert client.post("/api/members/me/withdraw", json={"password": "password123"}).status_code == 204
    client.cookies.clear()
    assert login(client).status_code == 401
    row = sql("SELECT login_id, name, phone, email, password FROM member")[0]
    assert dict(row) == {"login_id": f"withdrawn_{me['memberId']}", "name": "탈퇴회원", "phone": None, "email": None,
                         "password": "!"}
    assert sql("SELECT COUNT(*) AS n FROM reservation")[0]["n"] == 1  # 예약 기록은 남는다
    assert signup(client).status_code == 201  # 같은 아이디로 다시 가입 가능


def test_password_reset_with_email(client):
    signup(client, email="a@example.com")
    signup(client, "no_mail")

    def reset(**kw):
        body = {"loginId": "guest01", "email": "a@example.com", "newPassword": "resetpass1", **kw}
        return client.post("/api/members/password-reset", json=body)

    assert reset(email="b@example.com").json()["detail"]["code"] == "NOT_MATCHED"
    assert reset(loginId="no_mail", email="").json()["detail"]["code"] == "NOT_MATCHED"  # 이메일 없는 회원
    assert reset(email="A@Example.com ").status_code == 204  # 대소문자 · 공백 무시
    assert login(client, password="resetpass1").status_code == 200


def test_password_reset_refuses_admin(client):
    """이메일만 알면 관리자 계정을 가져갈 수 있던 문제(11-25): 관리자는 틀렸을 때와 같은 답으로 거절"""
    create_admin.create_admin("boss01", "관리자", "adminpass1")
    login(client, "boss01", "adminpass1")
    assert client.put("/api/members/me", json={"name": "관리자", "email": "boss@example.com"}).status_code == 200
    client.cookies.clear()

    r = client.post("/api/members/password-reset",
                    json={"loginId": "boss01", "email": "boss@example.com", "newPassword": "stolenpass1"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "NOT_MATCHED"
    assert r.json()["detail"]["message"] == "아이디와 가입한 이메일이 맞지 않습니다."  # 손님이 틀렸을 때와 같은 문구
    assert login(client, "boss01", "stolenpass1").status_code == 401  # 비밀번호는 그대로
    assert login(client, "boss01", "adminpass1").status_code == 200


def test_admin_cannot_withdraw_and_create_admin(client):
    assert create_admin.create_admin("boss01", "관리자", "adminpass1") == "created"
    assert login(client, "boss01", "adminpass1").json()["role"] == "ADMIN"
    r = client.post("/api/members/me/withdraw", json={"password": "adminpass1"})
    assert r.json()["detail"]["code"] == "ADMIN_CANNOT_WITHDRAW"
    signup(client, "guest02")
    assert create_admin.create_admin("guest02", "무시됨", "promoted1") == "promoted"
    assert login(client, "guest02", "promoted1").json()["role"] == "ADMIN"
    with pytest.raises(ValueError):
        create_admin.create_admin(create_admin.DEV_ADMIN_ID, "관리자", "short")  # 8자 미만 거부


def test_menus_follow_role(client, seeded_db):
    names = lambda: [m["menuName"] for m in client.get("/api/menus").json()]  # noqa: E731
    assert names() == ["객실 추천", "내 예약"]  # 로그인 안 함 = 손님 메뉴
    create_admin.create_admin("boss01", "관리자", "adminpass1")
    login(client, "boss01", "adminpass1")
    assert {"객실 관리", "예약 일자 관리", "예약 관리"} <= set(names())


# ---------- 아이디 중복확인 ----------

def check_id(client, login_id):
    return client.get("/api/members/check-id", params={"loginId": login_id})


def test_check_id_available_then_taken_ignoring_case(client):
    r = check_id(client, "guest01")
    assert r.status_code == 200 and r.json() == {"available": True, "message": "사용할 수 있는 아이디입니다."}
    signup(client)
    for login_id in ("guest01", "GUEST01", " guest01 "):
        assert check_id(client, login_id).json()["available"] is False
    assert check_id(client, "guest02").json()["available"] is True


@pytest.mark.parametrize("login_id", ["abc", "한글아이디", "bad id!", "a" * 51])
def test_check_id_rejects_bad_format(client, login_id):
    r = check_id(client, login_id)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "INVALID_LOGIN_ID"


def test_check_id_needs_login_id(client):
    assert client.get("/api/members/check-id").status_code == 422
