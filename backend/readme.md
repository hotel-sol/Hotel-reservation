# backend — FastAPI 서버 하나

모든 파트의 API가 `uvicorn main:app` 하나로 뜹니다. API는 `/api/...`, 임시 HTML 화면은 그대로(`/login` 등) 열립니다.

## 처음 한 번
```
cd backend
pip install -r requirements.txt
copy .env.example .env          # macOS · Linux: cp .env.example .env  → 값 채우기(커밋 금지)
python -m db.init_db            # 로컬 DB(hotel)를 지우고 팀 DDL + 개발용 데이터로 다시 만듦
```
- DB는 **각자 PC의 MariaDB**(로컬)입니다. `init_db`는 DB를 지우므로 `DB_HOST`가 `127.0.0.1` · `localhost`일 때만 실행됩니다.
- `.env`에 `ADMIN_PASSWORD`(팀 공용 비밀번호, 팀 채팅으로 받음)를 넣고 `init_db`를 실행하면 관리자 `admin01`이 생깁니다.

## 실행 · 테스트 (backend 폴더에서)
```
uvicorn main:app --reload       # http://127.0.0.1:8000/docs (API 목록), /login (임시 화면)
python -m pytest                # 파트별 테스트 DB(hotel_test …)를 새로 만들어 테스트
```

## 폴더
| 위치 | 하는 일 |
|---|---|
| `main.py` | 진입점. 아래 파트의 `router`를 `/api` 아래에, `pages`(임시 HTML 화면)를 그대로 붙임. **고칠 필요 없음** |
| `db/connect.py` | 공용 DB 연결 `connect()`, `get_db()`. `.env`를 읽음 |
| `db/init_db.py`, `db/dev_seed.sql` | 로컬 개발 DB 만들기, 화면설계서 12월 예시와 같은 가상 데이터 |
| `common/common.py` | 공통 오류 `fail(상태, "CODE", "메시지")`, `LIVE_STATUSES`(대기 + 승인), `today_kst()` |
| `member/` | 회원 · 로그인. 다른 파트는 `Depends(current_member)`, `Depends(require_admin)`을 가져다 씀 |
| `room/`, `roomdate/`, `reservation/` | 파트별 API |

## 새 파트 API 붙이기
`backend/<파트>/<파트>.py`에 `router`만 만들면 `main.py`가 자동으로 붙입니다.
```python
from fastapi import APIRouter, Depends

from common.common import fail
from db.connect import get_db
from member.member import require_admin

router = APIRouter(prefix="/admin/rooms", tags=["객실 관리"])   # 실제 주소: /api/admin/rooms


@router.get("")
def list_rooms(_admin: dict = Depends(require_admin), db=Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM room ORDER BY room_id")
        return cur.fetchall()
```
- 각자 만든 `get_connection()` · `FastAPI()` 앱은 지우고 위처럼 공용 것을 씁니다.
- 테스트는 `from main import app`으로 앱 전체를 띄우고, 픽스처에서 `monkeypatch.setenv("DB_NAME", "hotel_test_<파트>")` 후 `init_db("hotel_test_<파트>")`로 자기 테스트 DB를 만듭니다(예: `roomdate/test_roomdate.py`).
