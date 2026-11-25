def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_me_requires_login(client):
    res = client.get("/api/members/me")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "UNAUTHORIZED"


def test_recommend_validates_dates(client):
    res = client.get("/api/rooms/recommend", params={"checkIn": "2026-12-10"})
    assert res.status_code == 400


# ---- #70 보안 점검 ----

def test_health_db_does_not_expose_version(client):
    r = client.get("/api/health/db")
    assert r.status_code == 200 and r.json() == {"status": "ok"}  # DB 종류 · 버전을 알려 주지 않음


def test_weak_session_secret_rejected_outside_local():
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    strong = "x" * 32
    for weak in ("change-me", "short-secret"):
        with pytest.raises(ValidationError):
            Settings(app_env="production", session_secret=weak)  # 시연 · 배포 서버는 시작 거부
        with pytest.warns(UserWarning):
            Settings(app_env="local", session_secret=weak)  # 내 컴퓨터는 경고만 (팀원 개발이 멈추지 않게)
    assert Settings(app_env="production", session_secret=strong).session_secret == strong
