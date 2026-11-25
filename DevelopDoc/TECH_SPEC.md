# TECH_SPEC — 태양의 호텔 기술 명세

- 기준: dev `ee4a061`, 2026-11-25 (Step 3 · 점검 반영, PR #94까지). 직전 판: [docs/archive/2026-11-25_step3/DevelopDoc/TECH_SPEC.md](../docs/archive/2026-11-25_step3/DevelopDoc/TECH_SPEC.md) · 그 전 판: [docs/archive/2026-11-25_step2/DevelopDoc/TECH_SPEC.md](../docs/archive/2026-11-25_step2/DevelopDoc/TECH_SPEC.md)
- 구조 그림(전체 구조 · ERD · 예약 흐름 · 상태 · 휴무 지정 · 로그인): [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- API 입력 · 출력 전체: 백엔드를 켜고 http://localhost:8000/docs

## 1. 기술 스택

| 영역 | 사용 | 버전 |
|---|---|---|
| 화면 | Next.js(App Router) + React + Tailwind CSS | Next 16, React 19 |
| 백엔드 | FastAPI + SQLAlchemy 2 + psycopg 3 | Python 3.12 |
| DB | Supabase PostgreSQL (팀 프로젝트 1개, 도쿄 리전) | PostgreSQL 17 |
| 사진 저장 | Supabase Storage 버킷 `room-photos` (`SUPABASE_URL` · `SUPABASE_SECRET_KEY`가 있을 때), 없으면 `backend/uploads/` | |
| 패키지 · 실행 | `uv`(백엔드), `npm`(화면) | |
| 테스트 | pytest + httpx (백엔드), `tsc` · ESLint · `next build`(화면) | |

## 2. 구조

```
Hotel-reservation/
├── frontend/        Next.js. 화면은 src/app/, API 호출은 src/lib/api/, 공통 컴포넌트 src/components/
│                    next.config.ts rewrites: /api/* · /uploads/* → 백엔드(:8000)
├── backend/         FastAPI. app/api/routes(API) · app/models(테이블) · app/schemas(요청·응답)
│   │                app/services(추천 · 빈방 · 예약 확인/요금 · 사진 저장)
│   ├── app/db/      init_db.py(스키마 재생성), dev_seed.sql(테스트용), demo_seed.sql(시연용 40실)
│   └── tests/       pytest (각자 hotel_<이름>_test 스키마). 테스트 데이터는 tests/helpers.py로만 넣음
├── docs/            ARCHITECTURE.md, hotel_reservation_ddl.sql(테이블 기준), archive/(과거 설계 · 이전 판 문서)
└── DevelopDoc/      PRD · TECH_SPEC · WORK_UNITS · FINAL_CHECKLIST
```

- 브라우저는 화면 주소 하나만 봅니다. Next.js가 `/api/*`를 백엔드로 넘겨서 로그인 쿠키가 그대로 동작하고 CORS가 필요 없습니다.
- 모든 API는 `/api` 아래입니다. 요청 · 응답 JSON 이름은 camelCase(`roomId`, `checkInDate`)입니다.
- 오류 형식: `{"detail": {"code": "영문_대문자", "message": "화면에 띄울 문장", ...}}`. 화면은 `message`를 그대로 보여 줍니다.
- 주소 · 폼에 DB 숫자 범위를 넘는 번호(예: `/api/rooms/99999999999999999999`)는 500 대신 404 `NOT_FOUND` (`main.py`의 DataError 22003 처리, 모든 API 공통).

## 3. DB

테이블 정의 기준은 [`docs/hotel_reservation_ddl.sql`](../docs/hotel_reservation_ddl.sql)입니다(SQLAlchemy `create_all`은 쓰지 않음). 테이블 10개, Step 3 변경은 Discussion #60.

| 테이블 | 담당 파트 | 내용 |
|---|---|---|
| `member` | 1 | 회원. `role` = `USER` · `ADMIN`. 아이디 · 이메일은 대소문자 무시 UNIQUE. 탈퇴하면 행은 남기고 개인정보만 지움(아이디는 `withdrawn-<번호>`, 예약 FK 보존) |
| `room_view` | 1 | 조회 기록. PK `(room_id, viewer_key, view_date)` → 같은 사람 · 같은 방 · 같은 날은 1번. 회원 `M:<번호>`, 비회원은 모두 `G` 하나 |
| `login_attempt` | 1 | 로그인 · 비밀번호 확인 실패 기록(최근 10분 5번이면 잠금). 서버를 다시 켜도 유지 |
| `room_grade` | 2 | 객실 등급 S 로얄 스위트(기준 인원 4) · A 이그제큐티브 스위트 · B 프리미어 · C 디럭스(기준 인원 2). 기준 요금 · 인원 · 면적 · 침대. DDL에 기준 데이터 포함 |
| `room` | 2 | 객실. `room_name` 중복 불가, `is_active` = `Y` · `N`(삭제 대신 비활성), `view_count`, `grade_id` → `room_grade`, `view_type`(RIVER · CITY · MOUNTAIN), `bed_type` |
| `closure` | 3 | 휴무 묶음(한 번 지정한 하루 · 기간 = 1개). `reason_code` = `CONSTRUCTION` · `MAINTENANCE` · `EVENT` · `CLOSURE` · `ETC`, `reason`(상세), `created_by`(지정한 관리자) |
| `closed_date` | 3 | 휴무일. `room_id` NULL = 호텔 전체. `closure_id` NOT NULL → `closure`(묶음을 지우면 함께 삭제). `UNIQUE NULLS NOT DISTINCT (room_id, closed_date)`로 같은 날 중복 차단. 사유 칸(`reason`)은 없어지고 묶음으로 옮김 |
| `reservation` | 4 | 예약. `status` = `PENDING` · `APPROVED` · `CANCELED`, `price_per_night`(예약 때 1박 요금, NOT NULL) · `total_price`는 서버 계산, 취소 기록 `canceled_at` · `canceled_by` · `cancel_reason` |
| `attach_file` | 5(공통) | 첨부파일. 지금은 객실 사진만(`target_type='ROOM'`) |
| `menu` | 5(공통) | 상단 메뉴. `role`별로 보여 줌 |

**예약 제약 (Step 3 ③단계)**

- `ck_reservation_canceled`: `CANCELED` ↔ `canceled_at`이 있음.
- `ex_reservation_no_overlap`: 살아 있는 예약(대기 · 승인)끼리 같은 방에서 `[체크인, 체크아웃)`이 겹치면 저장 불가. 위반(SQLSTATE 23P01)은 API가 409 `ROOM_NOT_AVAILABLE`로 바꿈. `btree_gist` 확장이 필요해서 팀 Supabase에 `extensions` 스키마로 한 번 켜 둠(DDL에는 넣지 않음, 새 DB면 먼저 `CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA extensions;`).
- 인덱스: `idx_reservation_member`, `idx_reservation_live`(살아 있는 예약만). 옛 날짜 · 상태 인덱스 2개는 삭제.

**스키마 나누기 (한 프로젝트를 5명이 씀)**

| 용도 | `DB_SCHEMA` | 지우고 다시 만들기 |
|---|---|---|
| 각자 개발 | `hotel_<이름>` | `uv run python -m app.db.init_db` (`DB_RESET_ALLOWED=true`) |
| 각자 테스트 | `hotel_<이름>_test` | pytest가 매번 |
| 시연 · 통합 확인 | `hotel`(공용) | 팀에 알리고 `--reset-shared`를 붙였을 때만. 시연 데이터는 `--demo` |

- 시간: DB 시간대 `Asia/Seoul`(11-24 변경, 그전 기록은 UTC). "오늘"은 백엔드 `today_kst()`.
- 연결: Session pooler(5432). 무료 플랜이라 서버 하나가 연결을 최대 5개만 씁니다.
- DB 파일(DDL · 시드 · `tests/conftest.py` · `tests/helpers.py`)은 DB 담당이 고칩니다(팀 규칙, Discussion #60).

## 4. 로그인 · 권한 · 보안

| 항목 | 방식 |
|---|---|
| 비밀번호 저장 | scrypt 해시 |
| 가입 입력 | 아이디 영문 · 숫자 · `_` 4~20자, 비밀번호 8~64자 |
| 로그인 유지 | 서명한 세션 쿠키(회원 번호 + 비밀번호 표식, 8시간), HttpOnly · SameSite=Lax, 로컬이 아니면 Secure(HTTPS 필요). `APP_ENV`가 `local`이 아니면 `SESSION_SECRET`이 `change-me` · 32자 미만일 때 서버가 시작하지 않음(#70, local은 경고만) |
| 비밀번호 변경 | 다른 기기 로그인은 끊기고 지금 기기는 유지(쿠키의 비밀번호 표식이 달라짐) |
| 잘못된 비밀번호 | 10분 안에 5번 틀리면 10분 잠금(429). 기록은 `login_attempt` 테이블. 로그인에 성공한 적 있는 기기(서명한 `hotel_device` 쿠키)는 따로 세서 남이 일부러 잠가도 주인은 들어올 수 있음 |
| 비밀번호 찾기 | 시연 전까지 꺼 둠(403 `PASSWORD_RESET_DISABLED`). 이메일만 알면 남의 계정을 바꿀 수 있었기 때문 |
| 권한 | 로그인 필요 API는 `CurrentMember`, 관리자 API는 `require_admin` → 로그인 안 됨 401, 관리자 아님 403 |
| 동시 요청 | 예약 저장은 회원 행 → 객실 행 순서로 잠금, 휴무 지정은 대상 객실 행 잠금(호텔 전체면 모든 방), 객실 비활성화도 객실 행 잠금 → 서로 엇갈려 저장되지 않음 |
| 비밀값 | `.env`에만(커밋 금지). `.env.example`에 이름만 |

## 5. API

| 파트 | 메서드 · 주소 (`/api` 생략) | 설명 |
|---|---|---|
| 공통 | `GET health`, `GET health/db` | 서버 · DB 연결 확인 (`{"status":"ok"}`만, DB 버전은 안 보여 줌 — #70) |
| 1 | `POST members/signup · login · logout`, `GET PUT members/me`, `PUT members/me/password`, `POST members/me/withdraw` | 회원 |
| 1 | `POST members/password-reset` | 지금은 항상 403 (꺼 둠) |
| 1 | `GET rooms/recommend?checkIn&checkOut&guests&sort&page&size` | 추천. `sort` = `recommend` · `popular` · `price`, 뱃지 `BEST` · `HOT` · `NEW` |
| 1 | `GET members/check-id?loginId=` | 아이디 중복 확인 |
| 1 · 4 | `GET rooms/{id}`, `POST rooms/{id}/view` | 객실 상세, 조회수 +1(같은 사람 · 방 · 날 1번) |
| 2 | `GET room-grades` | 객실 등급 목록(로그인 불필요) |
| 4 | `GET rooms/{id}/available-dates?month=`, `GET rooms/{id}/quote?checkIn&checkOut&guests` | 예약 달력의 막힌 날짜(지난 날 · 휴무 · 예약), 요금 견적(박수 · 총액, 로그인 불필요) |
| 4 | `POST reservations`, `GET reservations/me`, `GET reservations/{id}` | 예약 신청(로그인), 내 예약, 예약 상세(본인 · 관리자). 손님용 취소 API는 없음 |
| 2 | `GET POST admin/rooms`, `GET admin/rooms/summary`, `PUT admin/rooms/{id}`, `PATCH admin/rooms/{id}/status` | 객실 관리, 요약 카드 |
| 2 · 5 | `POST GET files`, `DELETE files/{id}` | 객실 사진 (관리자) |
| 3 | `GET admin/closed-dates?month&roomId`, `GET .../reservation-counts`, `GET .../available-rooms` | 그달 휴무, 날짜별 예약 수, 날짜별 남은 객실 수. `month` 연도는 2000~2100 |
| 3 | `POST admin/closed-dates`, `POST .../range`, `DELETE .../{id}`, `DELETE .../range?startDate&endDate&roomId` | 휴무 지정 · 기간 지정 · 해제 · 기간 해제(지정 · 해제 모두 최대 31일). 입력 `reasonCode` + `reason`(분류 없으면 기타, 상세 필수) |
| 3 | `GET admin/closures?month&roomId`, `DELETE admin/closures/{id}` | 그달에 걸친 휴무 묶음(기간 · 사유 · 상태 `SCHEDULED` 예정 · `ACTIVE` 진행 중 · `ENDED` 종료), 묶음 해제 |
| 5 | `GET admin/reservations`, `GET admin/reservations/counts`, `PATCH admin/reservations/{id}/approve · cancel` | 예약 관리, 상태별 건수. 취소하면 `canceled_at` · `canceled_by` 기록 |
| 5 | `GET menus` | 역할별 메뉴 |

## 6. 주요 오류 코드

| 코드 | 상태 | 언제 |
|---|---|---|
| `DATE_CLOSED` | 409 | 예약 기간에 호텔 전체 휴무일이 있음 (여러 이유가 겹치면 이 코드가 먼저) |
| `ROOM_CLOSED` | 409 | 예약 기간에 그 객실만 판매 중지된 날이 있음 |
| `ROOM_NOT_AVAILABLE` | 409 | 예약 기간에 다른 예약(대기 · 승인)이 있음. DB 이중 예약 제약 위반(23P01)도 이 코드 |
| `TOO_MANY_PENDING` | 409 | 그 회원의 승인 대기 예약(체크아웃 전)이 이미 3건 |
| `PAST_DATE` · `INVALID_DATES` | 400 | 지난 체크인 날짜 · 체크아웃이 체크인보다 빠르거나 같음 |
| `TOO_LONG_STAY` · `TOO_FAR_DATE` | 400 | 6박 초과 · 체크인이 오늘부터 30일 뒤 (예약 · 견적 · 추천 검색 공통) |
| `TOO_MANY_GUESTS` | 400 | 인원이 객실 최대 인원보다 많음 |
| `ALREADY_CLOSED` | 409 | 이미 휴무(호텔 전체 휴무일에 객실 휴무를 넣는 경우 포함) |
| `CLOSED_DATE_CONFLICT` | 409 | 휴무로 지정하려는 날에 묵는 예약이 있음. 기간 지정이면 `detail.blockedDates`에 막힌 날짜 전부 |
| `RANGE_TOO_LONG` | 400 | 휴무 지정 · 해제 기간이 31일 초과 |
| `INVALID_MONTH` | 400 | `month`의 연도가 2000~2100 밖 |
| `FUTURE_RESERVATION_EXISTS` | 409 | 앞으로 묵을 예약이 있는 객실의 종류 · 인원 · 요금 수정, 또는 비활성화 |
| `INVALID_FILE_TYPE` · `FILE_TOO_LARGE` · `TOO_MANY_FILES` | 400 · 400 · 409 | 사진이 jpg · png가 아님 · 5MB 초과 · 객실당 5장 초과 |
| `STORAGE_FAILED` | 502 | Supabase Storage에 사진을 올리지 못함 |
| `INVALID_STATUS` · `PAST_CHECK_IN` | 409 | 바꿀 수 없는 예약 상태 · 체크인이 지난 승인 예약 취소 / 지난 대기 예약 승인 |
| `TOO_MANY_ATTEMPTS` | 429 | 비밀번호를 10분 안에 5번 틀림 |
| `PASSWORD_RESET_DISABLED` | 403 | 비밀번호 찾기(꺼 둠) |
| `NOT_FOUND` | 404 | DB 숫자 범위를 넘는 번호 등 |

- 객실 입력 범위: 1박 요금 1 ~ 10,000,000원, 최대 인원 1 ~ 20명(넘으면 422).

## 7. 테스트와 품질

| 무엇 | 명령 | 기준 |
|---|---|---|
| 백엔드 테스트 | `backend`에서 `uv run pytest` | 전부 통과 (11-25 dev `ee4a061` 기준 198개) |
| 화면 타입 · 규칙 | `frontend`에서 `npx tsc --noEmit`, `npm run lint` | 오류 0 |
| 화면 빌드 | `frontend`에서 `npm run build` | 통과 (Next 16 `cacheComponents`: `useSearchParams` 등은 Suspense 안) |

PR 전에 위 세 가지를 돌립니다. 테스트에서 DB 행은 `tests/helpers.py`의 함수로만 넣습니다(칸이 늘어도 한 곳만 고치면 되게).

## 8. 브랜치 · 배포

- 브랜치: `main`(제출 · 시연) · `dev`(통합, 기본 브랜치) · `feature/<파트>-<내용>`. 기능 PR은 dev로, main은 dev에서 온 PR만. 자세한 규칙은 [README](../README.md)의 브랜치 규칙.
- 팀 규칙 R1~R8은 GitHub Discussion #60 (DB 파일은 DB 담당이 고침, 테스트 데이터는 `tests/helpers.py`로만 등).
- 보호 규칙(ruleset)은 11-23에 해제했고 지금은 약속으로 지킵니다.
- 시연 배포: **미정**. 정할 것 — 배포 담당 · 주소, HTTPS(로그인 쿠키가 Secure), `BACKEND_URL` · `APP_ENV=production` · 32자 이상 무작위 `SESSION_SECRET`(`python -c "import secrets; print(secrets.token_hex(32))"`). 실제 화면 테스트 목록: [RELEASE_TEST](RELEASE_TEST.md). 관리 화면에서 올린 사진은 `SUPABASE_URL` · `SUPABASE_SECRET_KEY`를 넣으면 Storage 버킷 `room-photos`(`<DB_SCHEMA>/rooms/` 아래)에, 없으면 백엔드 PC의 `backend/uploads/`에 저장됩니다.
