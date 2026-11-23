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


def test_pages_and_get_logout():
    assert "회원가입" in client.get("/signup").text
    assert "로그인" in client.get("/login").text
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
