def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_me_requires_login(client):
    res = client.get("/api/members/me")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "UNAUTHORIZED"


def test_recommend_validates_dates(client):
    res = client.get("/api/rooms/recommend", params={"checkIn": "2026-12-10"})
    assert res.status_code == 400
