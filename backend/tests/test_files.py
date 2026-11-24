"""객실 사진 업로드 (ADM-001, POST /api/files) — jpg·png 만, 객실당 5장, 관리자만."""
import io

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

JPG = b"\xff\xd8\xff\xe0" + b"0" * 100  # jpg 머리 + 아무 내용
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
ADMIN_PW = "admin-test-pw"


@pytest.fixture(autouse=True)
def cleanup_uploads():
    """테스트가 만든 사진 파일은 끝나면 지운다 (내 uploads/ 폴더를 어지르지 않게)."""
    from pathlib import Path

    rooms = Path(get_settings().upload_dir) / "rooms"
    before = set(rooms.glob("*")) if rooms.exists() else set()
    yield
    for p in (set(rooms.glob("*")) if rooms.exists() else set()) - before:
        p.unlink(missing_ok=True)


@pytest.fixture
def admin(client, seeded_db):
    """1번 ADMIN 의 비밀번호를 알려진 값으로 바꾸고 로그인."""
    from app.core.security import hash_password

    with engine.begin() as c:
        c.execute(text("UPDATE member SET password = :p WHERE member_id = 1"), {"p": hash_password(ADMIN_PW)})
        login_id = c.execute(text("SELECT login_id FROM member WHERE member_id = 1")).scalar()
    r = client.post("/api/members/login", json={"loginId": login_id, "password": ADMIN_PW})
    assert r.status_code == 200, r.text
    return client


def upload(client, name="room.jpg", data=JPG, room_id=1, target="ROOM"):
    return client.post(
        "/api/files",
        data={"targetType": target, "targetId": str(room_id)},
        files={"file": (name, io.BytesIO(data), "application/octet-stream")},
    )


def test_upload_jpg_saves_file_and_row(admin):
    r = upload(admin)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["targetType"] == "ROOM" and body["targetId"] == 1
    assert body["originalName"] == "room.jpg"
    assert body["savedPath"].startswith("uploads/rooms/") and body["savedPath"].endswith(".jpg")
    saved = get_settings().upload_dir + "/rooms/" + body["savedPath"].split("/")[-1]
    with open(saved, "rb") as f:
        assert f.read() == JPG
    # 정적 파일로 보인다 (화면은 /uploads/... 로 연다)
    assert admin.get("/" + body["savedPath"]).content == JPG
    # 추천 카드의 대표 사진이 된다
    thumbs = {i["roomId"]: i["thumbnailUrl"] for i in admin.get("/api/rooms/recommend").json()["items"]}
    assert thumbs[1] == body["savedPath"]


def test_png_allowed(admin):
    assert upload(admin, "room.PNG", PNG).status_code == 201


@pytest.mark.parametrize("name,data", [
    ("room.gif", b"GIF89a" + b"0" * 10),   # 확장자 거부
    ("fake.jpg", b"not really a jpg"),      # 확장자만 jpg
    ("room.png", JPG),                       # 확장자와 내용 불일치
])
def test_only_real_jpg_png(admin, name, data):
    r = upload(admin, name, data)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_FILE_TYPE"


def test_max_five_per_room(admin):
    for _ in range(5):
        assert upload(admin).status_code == 201
    r = upload(admin)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "TOO_MANY_FILES"
    assert upload(admin, room_id=2).status_code == 201  # 다른 방은 따로 센다


def test_db_failure_removes_saved_file(admin, monkeypatch):
    """DB 기록(commit)이 실패하면 디스크에 쓴 파일도 지워서, 화면에 안 보이는 파일이 남지 않는다."""
    from pathlib import Path

    from sqlalchemy.orm import Session

    rooms = Path(get_settings().upload_dir) / "rooms"
    before = set(rooms.glob("*")) if rooms.exists() else set()

    def broken_commit(self):
        raise RuntimeError("DB 저장 실패 흉내")

    monkeypatch.setattr(Session, "commit", broken_commit)
    with pytest.raises(RuntimeError):
        upload(admin)
    monkeypatch.undo()

    assert set(rooms.glob("*")) - before == set()
    assert admin.get("/api/files", params={"targetType": "ROOM", "targetId": 1}).json() == []


def test_unknown_room_and_target(admin):
    assert upload(admin, room_id=9999).status_code == 404
    assert upload(admin, target="MEMBER").status_code == 400


def test_list_and_delete(admin):
    first = upload(admin).json()
    upload(admin, "b.png", PNG)
    files = admin.get("/api/files", params={"targetType": "ROOM", "targetId": 1}).json()
    assert [f["fileId"] for f in files][0] == first["fileId"]
    assert len(files) == 2

    assert admin.delete(f"/api/files/{first['fileId']}").status_code == 204
    left = admin.get("/api/files", params={"targetType": "ROOM", "targetId": 1}).json()
    assert [f["originalName"] for f in left] == ["b.png"]
    assert admin.get("/" + first["savedPath"]).status_code == 404  # 파일도 지워짐


def test_guest_and_anonymous_blocked(client, seeded_db):
    assert upload(client).status_code == 401
    r = client.post("/api/members/signup", json={"loginId": "guest_up", "password": "guest1234", "name": "손님"})
    assert r.status_code in (200, 201), r.text
    client.post("/api/members/login", json={"loginId": "guest_up", "password": "guest1234"})
    assert upload(client).status_code == 403
