# roomdate — 예약 일자(휴무일) 관리

담당 테이블 `closed_date`, 화면 ADM-002(관리자 예약 일자 관리). FastAPI `APIRouter`라서 메인 앱에 `app.include_router(roomdate.router)` 한 줄로 붙습니다.

## API
| 메서드 · 경로 | 설명 | 오류 |
|---|---|---|
| `GET /admin/closed-dates?month=2026-12[&roomId=1]` | 그달 휴무일 + 날짜별 예약 수(대기 + 승인) + 객실 목록(① 선택용) | — |
| `POST /admin/closed-dates` `{"closedDate": "2026-12-31", "roomId": null, "reason": "연말 시설 점검"}` | 휴무 지정. `roomId` 없으면 호텔 전체 | 400 `PAST_DATE` · `INVALID_INPUT`, 404 없는 객실, 409 `ALREADY_CLOSED` · `CLOSED_DATE_CONFLICT`("이 날짜에 예약 N건이 있습니다…") |
| `DELETE /admin/closed-dates/{closedDateId}` | 휴무 해제 | 404 |

공통: 관리자만(401 / 403). 오류 응답은 `{"detail": {"code", "message"}}`.

## 화면 (ADM-002 본문 ①~④)
`GET /admin/closed-dates/page` → `roomdate.html`(외부 라이브러리 없음). **상단 메뉴(객실 관리 · 예약 일자 관리 · 예약 관리 · 로그아웃)는 공통 레이아웃 담당이 만든다는 가정**이라 넣지 않았습니다.

시나리오(화면설계서 예시): 12월로 이동 → 31일 클릭 → ③ "이 날 예약 0건" → 사유 "연말 시설 점검" 입력 → [휴무일로 지정] → 31일에 "휴무", ④에 "12/31 전체 · 연말 시설 점검 [해제]". 예약 있는 날(15일)을 지정하면 ③에 "이 날짜에 예약 1건이 있습니다…"가 뜹니다.
- 지난 날짜는 누를 수 없음. 전체 객실 보기에서는 호텔 전체 휴무만 달력에 표시하고 방 휴무는 ④ 목록에만 보임.
- 화면도 임시 인증 헤더 `X-Member-Id: 1`을 보냄(`roomdate.html`의 `AUTH`).

## 실행
```
pip install -r requirements.txt
python init_db.py                 # 개발용 DB(hotel)를 지우고 다시 만듦. 공용 DB에 쓰지 말 것
uvicorn roomdate:app --reload     # 화면 http://127.0.0.1:8000/admin/closed-dates/page, API 문서 /docs
python -m pytest -q               # hotel_test DB를 새로 만들어 테스트
```
접속값은 환경변수 `DB_HOST`, `DB_PORT`(기본 3306), `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
`dev_schema.sql`은 팀 DDL(2026-11-20) 복사본, `dev_seed.sql`은 화면설계서 12월 예시와 같은 가상 데이터입니다(예약만 넣고 휴무일은 비워 둠. 12/31은 위 시나리오로 직접 지정).

## 정한 규칙 (기획문서에 없어서 정함, 확인 부탁)
- "그날 예약" = 그날 밤 묵는 예약(체크인 ≤ 그날 < 체크아웃). 체크아웃 날은 예약이 있어도 휴무 지정 가능.
- 호텔 전체 휴무: 어느 방이든 그날 예약이 있으면 거부. 방 휴무: 그 방 예약만 봄.
- 호텔 전체 휴무인 날에 방 휴무 추가 → `ALREADY_CLOSED`. 방 휴무가 있는 날에 호텔 전체 휴무는 가능.
- 오늘(한국 시간)부터 지정 가능. 사유는 필수(최대 200자).
- 인증은 임시: `X-Member-Id` 헤더의 회원 role이 ADMIN인지만 봄. 로그인이 나오면 `require_admin`만 바꿈.
- DB 연결은 임시로 이 파일 안에 있음. 공통 `db/connect.py`가 채워지면 그쪽으로 바꿈.

## DDL 참고
`UNIQUE (room_id, closed_date)`는 `room_id`가 NULL(호텔 전체 휴무)이면 같은 날 중복을 막지 못합니다(MySQL · MariaDB 공통, 직접 확인). 그래서 API에서 먼저 검사합니다.

## 예약 파트에 드릴 쿼리
예약 화면(`GET /rooms/{roomId}/available-dates`, `POST /reservations`)에서 휴무일을 막을 때:
```sql
-- 숙박 기간 [체크인, 체크아웃)에 호텔 전체 휴무나 그 방 휴무가 하루라도 있으면 1
SELECT EXISTS (
  SELECT 1 FROM closed_date
  WHERE (room_id IS NULL OR room_id = %s)
    AND closed_date >= %s AND closed_date < %s
) AS closed;
```
