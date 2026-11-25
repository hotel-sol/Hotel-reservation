"""#76 공통: 주소 · 폼에 DB 숫자 범위(BIGINT)를 넘는 아주 큰 번호를 넣어도 500 대신 404."""
import pytest

from tests.test_closed_dates import ADMIN, GUEST

pytestmark = pytest.mark.usefixtures("seeded_db")

BIG = "99999999999999999999"  # 20자리 > BIGINT 최대 9223372036854775807


@pytest.mark.parametrize("method, path, headers", [
    ("get", f"/api/rooms/{BIG}", {}),                                         # 1번 객실 상세 (로그인 없이)
    ("post", f"/api/rooms/{BIG}/view", {}),                                   # 1번 조회수
    ("get", f"/api/rooms/{BIG}/available-dates?month=2026-12", {}),           # 4번 예약 달력
    ("get", f"/api/rooms/{BIG}/quote?checkIn=2027-01-04&checkOut=2027-01-05&guests=1", {}),  # 4번 견적
    ("get", f"/api/reservations/{BIG}", GUEST),                               # 4번 예약 상세
    ("patch", f"/api/admin/reservations/{BIG}/approve", ADMIN),               # 5번 승인
    ("delete", f"/api/admin/closed-dates/{BIG}", ADMIN),                      # 3번 휴무 해제
    ("delete", f"/api/admin/closures/{BIG}", ADMIN),                          # 3번 묶음 해제
    ("patch", f"/api/admin/rooms/{BIG}/status", ADMIN),                       # 2번 사용 여부
    ("delete", f"/api/files/{BIG}", ADMIN),                                   # 2번 사진 삭제
])
def test_big_id_is_404_not_500(client, method, path, headers):
    kwargs = {"json": {"isActive": "N"}} if path.endswith("/status") else {}
    r = getattr(client, method)(path, headers=headers, **kwargs)
    assert r.status_code == 404, (path, r.status_code, r.text[:200])
    assert r.json()["detail"]["code"] == "NOT_FOUND"
