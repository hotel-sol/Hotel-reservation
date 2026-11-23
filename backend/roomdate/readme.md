# roomdate — 예약 일자(휴무일) 관리

담당 테이블 `closed_date`, 화면 ADM-002(관리자 예약 일자 관리). `router`(API)와 `pages`(임시 HTML 화면)를 `backend/main.py`가 자동으로 붙입니다.

## API (실제 주소는 앞에 `/api`, 예: `/api/admin/closed-dates`)
| 메서드 · 경로 | 설명 | 오류 |
|---|---|---|
| `GET /admin/closed-dates?month=2026-12[&roomId=1]` | 그달 휴무일 + 날짜별 예약 수(대기 + 승인) + 객실 목록(① 선택용) | — |
| `POST /admin/closed-dates` `{"closedDate": "2026-12-31", "roomId": null, "reason": "연말 시설 점검"}` | 휴무 지정. `roomId` 없으면 호텔 전체 | 400 `PAST_DATE` · `INVALID_INPUT`, 404 없는 객실, 409 `ALREADY_CLOSED` · `CLOSED_DATE_CONFLICT`("이 날짜에 예약 N건이 있습니다…") |
| `DELETE /admin/closed-dates/{closedDateId}` | 휴무 해제 | 404 |

공통: **관리자만**(401 / 403). 회원 기능(`backend/member`)의 로그인 세션으로 확인합니다(`Depends(require_admin)`). 오류 응답은 `{"detail": {"code", "message"}}`.

## 화면 (ADM-002)
`GET /admin/closed-dates/page` → `roomdate.html`(외부 라이브러리 없음). 위에 공통 상단 메뉴(`frontend/layout`)가 붙고 **관리자만 들어옵니다**(아니면 `/login?next=…`). 로그인이 풀리면 로그인 화면으로 갔다가 이 화면으로 돌아옵니다.

시나리오(화면설계서 예시): 12월로 이동 → 31일 클릭 → ③ "이 날 예약 0건" → 사유 "연말 시설 점검" 입력 → [휴무일로 지정] → 31일에 "휴무", ④에 "12/31 전체 · 연말 시설 점검 [해제]". 예약 있는 날(15일)을 지정하면 ③에 "이 날짜에 예약 1건이 있습니다…"가 뜹니다.
- 지난 날짜는 누를 수 없음. 전체 객실 보기에서는 호텔 전체 휴무만 달력에 표시하고 방 휴무는 ④ 목록에만 보임.

## 실행
실행 · 테스트 · 접속값은 [backend/readme.md](../readme.md)를 따릅니다(`uvicorn main:app` → http://127.0.0.1:8000/login → 예약 일자 관리, `python -m pytest`).
DB 구조는 팀 DDL `docs/hotel_reservation_ddl.sql`을 그대로 씁니다(복사본 없음). `db/dev_seed.sql`은 화면설계서 12월 예시와 같은 가상 데이터입니다(예약만 넣고 휴무일은 비워 둠. 12/31은 위 시나리오로 직접 지정).

## 정한 규칙 (기획문서에 없어서 정함, 확인 부탁)
- "그날 예약" = 그날 밤 묵는 예약(체크인 ≤ 그날 < 체크아웃). 체크아웃 날은 예약이 있어도 휴무 지정 가능.
- 호텔 전체 휴무: 어느 방이든 그날 예약이 있으면 거부. 방 휴무: 그 방 예약만 봄.
- 호텔 전체 휴무인 날에 방 휴무 추가 → `ALREADY_CLOSED`. 방 휴무가 있는 날에 호텔 전체 휴무는 가능.
- 오늘(한국 시간)부터 지정 가능. 사유는 필수(최대 200자).

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
