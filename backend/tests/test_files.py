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
def local_storage(monkeypatch):
    """테스트는 항상 내 컴퓨터(upload_dir)에 저장 — .env 에 Storage 키가 있어도 진짜 버킷에 올리지 않게."""
    monkeypatch.setattr(get_settings(), "supabase_secret_key", "")


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


# ---------- 2-A2 사진 공용 저장소 (Supabase Storage) — 진짜 버킷 대신 가짜 호출로 확인 ----------

@pytest.fixture
def fake_storage(monkeypatch):
    """Storage 설정을 켜고, 바깥으로 나가는 호출(_call)은 기록만 한다."""
    from app.services import photo_storage

    s = get_settings()
    monkeypatch.setattr(s, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(s, "supabase_secret_key", "sb_secret_test")
    calls = []
    monkeypatch.setattr(photo_storage, "_call", lambda method, url, data, ctype: calls.append((method, url, data, ctype)))
    return calls


def test_storage_upload_saves_public_url(admin, fake_storage):
    r = upload(admin)
    assert r.status_code == 201, r.text
    path = r.json()["savedPath"]
    folder = f"{get_settings().db_schema}/rooms/"  # 스키마별 폴더
    prefix = "https://example.supabase.co/storage/v1/object/public/room-photos/"
    assert path.startswith(prefix + folder) and path.endswith(".jpg")
    object_path = path[len(prefix):]
    assert fake_storage == [("POST", "https://example.supabase.co/storage/v1/object/room-photos/" + object_path, JPG, "image/jpeg")]
    # 추천 카드 대표 사진도 그 주소
    thumbs = {i["roomId"]: i["thumbnailUrl"] for i in admin.get("/api/rooms/recommend").json()["items"]}
    assert thumbs[1] == path


def test_storage_delete_removes_object(admin, fake_storage):
    import json

    f = upload(admin).json()
    assert admin.delete(f"/api/files/{f['fileId']}").status_code == 204
    method, url, data, _ = fake_storage[-1]
    object_path = f["savedPath"].split("/public/room-photos/")[1]
    assert (method, url) == ("DELETE", "https://example.supabase.co/storage/v1/object/room-photos")
    assert json.loads(data) == {"prefixes": [object_path]}


def test_storage_failure_returns_502_without_row(admin, monkeypatch, fake_storage):
    import urllib.error

    from app.services import photo_storage

    def down(*args):
        raise urllib.error.URLError("저장소 연결 안 됨 흉내")

    monkeypatch.setattr(photo_storage, "_call", down)
    r = upload(admin)
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "STORAGE_FAILED"
    assert admin.get("/api/files", params={"targetType": "ROOM", "targetId": 1}).json() == []


def test_demo_photo_delete_keeps_public_file(admin, fake_storage):
    """시연용 사진(room-photos/..., frontend/public)은 행만 지우고 파일 · 버킷은 건드리지 않는다."""
    with engine.begin() as c:
        fid = c.execute(text(
            "INSERT INTO attach_file (target_type, target_id, original_name, saved_path, file_size)"
            " VALUES ('ROOM', 1, 'd.jpg', 'room-photos/deluxe/deluxe_01.jpg', 10) RETURNING file_id")).scalar()
    assert admin.delete(f"/api/files/{fid}").status_code == 204
    assert fake_storage == []


def test_concurrent_uploads_never_exceed_five(admin, monkeypatch):
    """#69: 4장 있는 방에 두 장을 동시에 올려도 5장까지만 (객실 행 잠금), 넘친 쪽 파일은 지운다."""
    import threading
    import time
    from pathlib import Path

    from fastapi.testclient import TestClient

    from app.api.routes import files
    from app.main import app

    for _ in range(4):
        assert upload(admin).status_code == 201
    rooms = Path(get_settings().upload_dir) / "rooms"
    before = set(rooms.glob("*"))

    # 첫 요청이 "잠금 뒤 다시 세기"를 마친 순간 멈춰 두고(아직 기록 전), 그때 두 번째 요청을 보낸다.
    # 잠금이 없으면 두 번째도 4장으로 세고 기록해서 6장이 된다.
    real_count = files.photo_count
    calls: dict[int, int] = {}
    first_counted = threading.Event()

    def count_then_pause(*args):
        n = real_count(*args)
        me = threading.get_ident()
        calls[me] = calls.get(me, 0) + 1
        if calls[me] == 2 and not first_counted.is_set():  # 요청마다 2번째 = 잠금 뒤 다시 세기
            first_counted.set()
            time.sleep(1.5)
        return n

    monkeypatch.setattr(files, "photo_count", count_then_pause)
    other = TestClient(app)
    other.cookies.update(admin.cookies)
    codes = []
    first = threading.Thread(target=lambda: codes.append(upload(admin).status_code))
    second = threading.Thread(target=lambda: codes.append(upload(other).status_code))
    first.start()
    assert first_counted.wait(10)
    second.start()
    first.join()
    second.join()
    assert sorted(codes) == [201, 409]
    assert len(admin.get("/api/files", params={"targetType": "ROOM", "targetId": 1}).json()) == 5
    assert len(set(rooms.glob("*")) - before) == 1  # 409 난 쪽이 먼저 올린 파일은 지워짐


def test_room_not_locked_while_saving_file(admin, monkeypatch):
    """PR #73 리뷰: 파일을 올리는 동안(Storage 는 느릴 수 있음) 객실 행을 잠그지 않는다
    → 그 방 손님 예약 · 호텔 전체 휴무 지정이 업로드를 기다리지 않는다."""
    from sqlalchemy.exc import OperationalError

    from app.services import photo_storage

    real_save = photo_storage.save
    seen = []

    def save_and_try_lock(*args):
        try:
            with engine.begin() as c:  # 다른 요청인 척: 그 방을 바로 잠글 수 있나 (NOWAIT = 잠겨 있으면 바로 오류)
                c.execute(text("SELECT room_id FROM room WHERE room_id = 1 FOR UPDATE NOWAIT"))
            seen.append("잠글 수 있음")
        except OperationalError:
            seen.append("이미 잠겨 있음")
        return real_save(*args)

    monkeypatch.setattr(photo_storage, "save", save_and_try_lock)
    assert upload(admin).status_code == 201
    assert seen == ["잠글 수 있음"]


def test_upload_does_not_block_server():
    """준엽님 점검: 업로드는 async 가 아닌 일반 함수 → FastAPI 가 스레드에서 돌려서, Storage 를 기다리는 동안
    다른 요청(예약 · 로그인)이 멈추지 않는다. async def 안에서 DB · HTTP 를 그냥 기다리면 서버 전체가 멈춘다."""
    import inspect

    from app.api.routes import files

    assert not inspect.iscoroutinefunction(files.upload_file)
