"""회원 API 통과 테스트. 실제 MariaDB에 hotel_test_member DB를 매번 새로 만든다(팀 DDL docs/hotel_reservation_ddl.sql).

실행: DB_PORT=3307 python -m pytest -q  (backend/member 폴더에서)
"""
import os

os.environ["DB_NAME"] = "hotel_test_member"  # member import 전에

from pathlib import Path

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

import member as m

DDL = Path(__file__).parent.parent.parent / "docs" / "hotel_reservation_ddl.sql"
client = TestClient(m.app)


@m.app.get("/test-admin-only")
def admin_only(admin: dict = Depends(m.require_admin)):
    return {"ok": True}


@pytest.fixture(autouse=True)
def fresh_db():
    conn = m.pymysql.connect(host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", "3306")),
                             user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD", ""))
    with conn.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS hotel_test_member")
        cur.execute("CREATE DATABASE hotel_test_member CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute("USE hotel_test_member")
        for stmt in DDL.read_text(encoding="utf-8").split(";"):
            code = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
            if code:
                cur.execute(code)
    conn.commit()
    conn.close()
    client.cookies.clear()
    m._fails.clear()


def signup(login_id="guest01", password="password123", **extra):
    return client.post("/members/signup", json={"loginId": login_id, "password": password, "name": "손님", **extra})


def login(login_id="guest01", password="password123"):
    return client.post("/members/login", json={"loginId": login_id, "password": password})


def stored_password(login_id):
    conn = m.connect()
    with conn.cursor() as cur:
        cur.execute("SELECT password FROM member WHERE login_id = %s", (login_id,))
        row = cur.fetchone()
    conn.close()
    return row["password"]


def test_signup_login_me_logout():
    r = signup(email="a@example.com", phone="010-1234-5678")
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "USER"

    assert client.get("/members/me").status_code == 401
    r = login()
    assert r.status_code == 200 and r.json()["loginId"] == "guest01"
    assert client.get("/members/me").json()["role"] == "USER"

    assert client.post("/members/logout").status_code == 204
    client.cookies.clear()  # TestClient는 삭제 쿠키를 그대로 들고 있어서 직접 비운다
    assert client.get("/members/me").status_code == 401


def test_password_is_salted_hash_not_plain():
    signup("user_a")
    signup("user_b")  # 같은 비밀번호
    a, b = stored_password("user_a"), stored_password("user_b")
    assert "password123" not in a
    scheme, salt, digest = a.split("$")
    assert scheme == "scrypt" and len(salt) == 32 and len(digest) == 128
    assert a != b                       # 소금이 달라서 같은 비밀번호도 저장값이 다르다
    assert m.verify_password("password123", a) and not m.verify_password("wrong-pass", a)


def test_signup_rules():
    assert signup().status_code == 201
    assert signup().json()["detail"]["code"] == "DUPLICATE_LOGIN_ID"
    assert signup("other1", email="x@example.com").status_code == 201
    assert signup("other2", email="x@example.com").json()["detail"]["code"] == "DUPLICATE_EMAIL"
    assert signup("ab").json()["detail"]["code"] == "INVALID_LOGIN_ID"
    assert signup("short_pw", password="1234567").status_code == 422
    assert signup("bad_mail", email="not-mail").json()["detail"]["code"] == "INVALID_EMAIL"
    r = client.post("/members/signup", json={"loginId": "sneaky", "password": "password123", "name": "x", "role": "ADMIN"})
    assert r.json()["role"] == "USER"   # 가입으로 관리자가 될 수 없다


def test_wrong_password_and_forged_cookie():
    signup()
    assert login(password="wrong-pass").status_code == 401
    assert login("nobody").json()["detail"]["message"] == "아이디 또는 비밀번호가 맞지 않습니다."
    client.cookies.set(m.SESSION_COOKIE, "1.9999999999.forged")
    assert client.get("/members/me").status_code == 401


def test_admin_only_dependency():
    signup()
    login()
    assert client.get("/test-admin-only").status_code == 403
    conn = m.connect()
    with conn.cursor() as cur:
        cur.execute("UPDATE member SET role = 'ADMIN' WHERE login_id = 'guest01'")
    conn.commit()
    conn.close()
    assert client.get("/test-admin-only").status_code == 200   # 역할 변경이 바로 반영


def run_sql(sql, params=()):
    conn = m.connect()
    with conn.cursor() as cur:
        cur.execute(sql, params)
    conn.commit()
    conn.close()


def test_login_locks_after_five_failures():
    signup()
    for _ in range(5):
        assert login(password="wrong-pass").status_code == 401
    assert login().status_code == 429                      # 맞는 비밀번호여도 잠김
    m._fails.clear()                                        # 10분 지난 것으로 치고
    assert login().status_code == 200


def test_update_profile():
    signup(email="a@example.com")
    signup("other1", email="b@example.com")
    login()
    r = client.put("/members/me", json={"name": "새이름", "phone": "010-1111-2222", "email": "new@example.com"})
    assert r.status_code == 200 and r.json()["name"] == "새이름"
    assert client.get("/members/me").json()["email"] == "new@example.com"
    r = client.put("/members/me", json={"name": "새이름", "email": "b@example.com"})
    assert r.json()["detail"]["code"] == "DUPLICATE_EMAIL"
    assert client.put("/members/me", json={"name": "   "}).status_code == 400


def test_change_password_logs_out_other_devices():
    signup()
    login()
    old_cookie = client.cookies.get(m.SESSION_COOKIE)
    r = client.put("/members/me/password", json={"currentPassword": "wrong-pass", "newPassword": "newpass123"})
    assert r.json()["detail"]["code"] == "WRONG_PASSWORD"
    r = client.put("/members/me/password", json={"currentPassword": "password123", "newPassword": "newpass123"})
    assert r.status_code == 204
    assert client.get("/members/me").status_code == 200    # 지금 기기는 새 쿠키로 계속 로그인
    client.cookies.set(m.SESSION_COOKIE, old_cookie)
    assert client.get("/members/me").status_code == 401    # 예전 쿠키(다른 기기)는 끊김
    client.cookies.clear()
    assert login(password="password123").status_code == 401
    assert login(password="newpass123").status_code == 200


def test_withdraw_keeps_reservation_rows():
    signup(email="a@example.com", phone="010-1234-5678")
    login()
    me = client.get("/members/me").json()
    run_sql("INSERT INTO room (room_name, room_type, max_guest, price) VALUES ('101호', 'STANDARD', 2, 80000)")
    run_sql("INSERT INTO reservation (member_id, room_id, check_in_date, check_out_date, guest_count, total_price, status)"
            " VALUES (%s, 1, CURDATE() + INTERVAL 5 DAY, CURDATE() + INTERVAL 6 DAY, 1, 80000, 'PENDING')",
            (me["memberId"],))
    r = client.post("/members/me/withdraw", json={"password": "password123"})
    assert r.json()["detail"]["code"] == "HAS_RESERVATION"   # 진행 중인 예약이 있으면 불가

    run_sql("UPDATE reservation SET status = 'CANCELED'")
    assert client.post("/members/me/withdraw", json={"password": "wrong-pass"}).status_code == 400
    assert client.post("/members/me/withdraw", json={"password": "password123"}).status_code == 204
    assert client.get("/members/me").status_code == 401
    assert login().status_code == 401
    conn = m.connect()
    with conn.cursor() as cur:
        cur.execute("SELECT login_id, name, phone, email, password FROM member")
        row = cur.fetchone()
        cur.execute("SELECT COUNT(*) AS n FROM reservation")
        kept = cur.fetchone()["n"]
    conn.close()
    assert row == {"login_id": f"withdrawn_{me['memberId']}", "name": "탈퇴회원", "phone": None, "email": None,
                   "password": "!"}
    assert kept == 1                                          # 예약 기록은 남는다
    assert signup().status_code == 201                        # 같은 아이디로 다시 가입 가능


def test_password_reset_with_email():
    signup(email="a@example.com")
    signup("no_mail")
    reset = lambda **kw: client.post("/members/password-reset",
                                     json={"loginId": "guest01", "email": "a@example.com", "newPassword": "resetpass1", **kw})
    assert reset(email="b@example.com").json()["detail"]["code"] == "NOT_MATCHED"
    assert reset(loginId="no_mail", email="").json()["detail"]["code"] == "NOT_MATCHED"  # 이메일 없는 회원
    assert reset(email="A@Example.com ").status_code == 204                             # 대소문자 · 공백 무시
    assert login(password="resetpass1").status_code == 200


def test_admin_cannot_withdraw_and_create_admin():
    import create_admin
    assert create_admin.create_admin("boss01", "관리자", "adminpass1") == "created"
    assert login("boss01", "adminpass1").json()["role"] == "ADMIN"
    assert client.post("/members/me/withdraw", json={"password": "adminpass1"}).json()["detail"]["code"] == \
        "ADMIN_CANNOT_WITHDRAW"
    signup("guest02")
    assert create_admin.create_admin("guest02", "무시됨", "promoted1") == "promoted"
    assert login("guest02", "promoted1").json()["role"] == "ADMIN"
    with pytest.raises(ValueError):
        create_admin.create_admin(create_admin.DEV_ADMIN_ID, "관리자", "short")   # 8자 미만 거부


def test_pages_and_get_logout():
    assert "회원가입" in client.get("/signup").text
    assert "로그인" in client.get("/login").text
    assert "회원 탈퇴" in client.get("/mypage").text
    assert "비밀번호 찾기" in client.get("/password-reset").text
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
