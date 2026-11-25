# Backend — FastAPI + Supabase(PostgreSQL)

- 기준: dev `ee4a061`, 2026-11-25 (Step 3 · 점검 반영, PR #94까지). 직전 판: [docs/archive/2026-11-25_step3/backend/README.md](../docs/archive/2026-11-25_step3/backend/README.md) · 그 전 판: [docs/archive/2026-11-25_step2/backend/README.md](../docs/archive/2026-11-25_step2/backend/README.md)

## 처음 한 번 (backend 폴더에서)

```bash
cp .env.example .env              # Windows: copy .env.example .env → 값 채우기 (커밋 금지)
uv sync                           # Python 3.12 + 패키지 설치
uv run python -m app.db.init_db   # 내 스키마(hotel_<이름>)를 지우고 팀 DDL + 개발용 데이터로 다시 만듦
```

- DB는 **Supabase(PostgreSQL) 팀 프로젝트 하나를 5명이 같이** 씁니다. 비밀번호는 팀 채팅으로만 주고받습니다(저장소 · 노션 금지).
- `SESSION_SECRET`: 로컬은 아무 값이나 되지만(짧으면 경고), `APP_ENV`가 `local`이 아니면 32자 이상 무작위 값이어야 서버가 켜집니다(#70). 만들기: `python -c "import secrets; print(secrets.token_hex(32))"`
- `.env`의 `DATABASE_URL`에는 프로젝트 → Connect → **Session pooler** URI를 넣습니다(Direct connection은 IPv6 전용이라 안 될 수 있음).
- 서로의 데이터를 지우지 않도록 **스키마로 나눕니다.**

  | 용도 | `DB_SCHEMA` | 지우고 다시 만들기 |
  |---|---|---|
  | 각자 개발 | `hotel_<영문 이름>` (예: `hotel_minhyuk`) | `init_db`로 언제든 (`DB_RESET_ALLOWED=true`) |
  | 각자 테스트 | 자동으로 `hotel_<이름>_test` | 테스트가 매번 |
  | 시연 · 통합 확인 | `hotel` (공용) | 팀에 알리고 `--reset-shared`를 붙였을 때만 |
- 열쇠(비밀번호)는 하나라서 남의 스키마도 기술적으로는 열립니다. **남의 스키마와 `hotel`은 지우거나 고치지 않는 것**이 규칙입니다.
- 무료 플랜은 동시 연결 수가 적어서 서버 하나가 연결을 최대 5개만 씁니다.
- 이중 예약 제약(`EXCLUDE`)에 `btree_gist` 확장이 필요합니다. 팀 프로젝트에는 `extensions` 스키마로 켜 두었고(DDL에는 없음), 새 DB라면 먼저 `CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA extensions;`.
- 객실 사진: `.env`에 `SUPABASE_URL` · `SUPABASE_SECRET_KEY`를 둘 다 넣으면 Storage 버킷 `room-photos`(`<DB_SCHEMA>/rooms/` 아래)에, 비워 두면 `uploads/rooms/`(내 컴퓨터)에 저장합니다.

## 실행 · 테스트

```bash
uv run fastapi dev app/main.py --port 8000   # http://localhost:8000/docs
uv run pytest                                # hotel_<이름>_test 스키마를 새로 만들어 테스트
```

- DB 연결 확인: http://localhost:8000/api/health/db (`{"status": "ok"}`, DB 버전은 안 보여 줌 — #70)
- 프론트(Next.js)는 `/api/*`를 이 서버로 넘깁니다. 같은 주소로 보여서 로그인 쿠키가 그대로 동작합니다.

## 구조

```
app/
├── main.py                 FastAPI 앱, CORS, /api 라우터 등록
├── core/
│   ├── config.py           .env → Settings (DB URL 조립)
│   ├── security.py         비밀번호 scrypt 해시, 세션 쿠키 서명(비밀번호 바뀌면 예전 쿠키 무효)
│   ├── exceptions.py       fail(status, code, message) 공통 에러
│   └── dates.py            today_kst() 오늘 날짜(한국 시간)
├── db/
│   ├── base.py · session.py   SQLAlchemy Base, engine, get_db()
│   ├── init_db.py          개발 DB 스키마 다시 만들기 (팀 DDL + dev_seed.sql)
│   ├── create_admin.py     관리자 계정 만들기
│   ├── dev_seed.sql        화면설계서 12월 예시와 같은 가상 데이터 (테스트 기준)
│   └── demo_seed.sql       시연용 40실 · 사진 (init_db --demo, 공용 hotel)
├── models/                 테이블 1개 = 파일 1개 (member, room, room_grade, reservation, closed_date, closure, attach_file, menu)
│                           room_view · login_attempt 는 모델 없이 SQL로 씀
├── schemas/                요청/응답 Pydantic 모델 (JSON 은 camelCase)
├── services/               비즈니스 로직
│   ├── room_service.py         추천 점수 · 뱃지 · 객실 상세
│   ├── availability_service.py 예약 달력 · 막힌 이유(지난 날 · 휴무 · 예약)
│   ├── reservation_service.py  예약 확인(6박 · 30일 · 대기 3건) · 요금 계산 한 곳
│   └── photo_storage.py        사진 저장 (Supabase Storage 또는 uploads/)
└── api/
    ├── deps.py             DB, CurrentMember, AdminMember 의존성
    ├── router.py           라우터 모음
    └── routes/
        ├── health.py · members.py · menus.py · rooms.py · room_grades.py · reservations.py · files.py
        └── admin/          rooms.py (ADM-001) · closed_dates.py (ADM-002, 휴무 묶음 closures 포함) · reservations.py (ADM-003)
tests/                      pytest (conftest.py 의 empty_db / seeded_db 픽스처, 행 넣기는 helpers.py 로만)
```

테이블 정의는 저장소의 `docs/hotel_reservation_ddl.sql` 하나가 기준입니다. 전체 구조 그림은 `docs/ARCHITECTURE.md`.

## 규칙

- 모든 API 는 `/api` 접두사. 에러는 `{"detail": {"code", "message"}}`.
- 로그인 필요: `member: CurrentMember`, 관리자 전용: `dependencies=[Depends(require_admin)]`.
- 테이블은 DDL로 만들므로 `create_all` 을 쓰지 않습니다. 스키마를 바꾸면 `docs/hotel_reservation_ddl.sql`을 고치고 모델도 맞춥니다.
- `reservation.updated_at` 은 상태 변경 코드에서 직접 갱신합니다.
- 예약이 차지하는 날은 `체크인 ≤ 날짜 < 체크아웃`, 살아 있는 예약은 `PENDING`·`APPROVED` (`models/reservation.py`의 `LIVE_STATUSES`).
- 비밀번호는 `scrypt$salt$hash` 형식. 로그인 · 비밀번호 확인을 10분 안에 5번 틀리면 10분 잠금(429, `login_attempt` 테이블).
- 같은 방 날짜 겹침은 코드 검사 + DB 제약 `ex_reservation_no_overlap`. 제약 위반(23P01)은 409 `ROOM_NOT_AVAILABLE`.
- DB 숫자 범위를 넘는 번호(DataError 22003)는 `main.py`에서 404 로 바꿉니다.
- DB 파일(DDL · 시드 · `tests/conftest.py` · `tests/helpers.py`)은 DB 담당이 고치고, 테스트는 `tests/helpers.py`로만 행을 넣습니다(팀 규칙, Discussion #60).

## 배포 (시연용, 무료)
| 구분 | 주소 | 서비스 |
|---|---|---|
| 화면 | https://hotel-reservation-ten-phi.vercel.app | Vercel (root `frontend`, env `BACKEND_URL`) |
| 서버 | https://hotel-sol-api.onrender.com | Render (root `backend`, env `APP_ENV=production` · `DB_SCHEMA=hotel` · `DATABASE_URL` · `SESSION_SECRET`) |

- `main`에 합쳐지면 둘 다 자동으로 다시 배포된다(Render는 `backend/` 안이 바뀔 때만).
- Render 무료 서버는 15분 쉬면 잠든다. 시연 전에 `/api/health`를 한 번 열어 깨운다(첫 응답 50초 안팎).
- DB 구조를 바꿀 때: Render 일시정지 → 공용 `hotel` 변경 → `main` 반영 → Render 재개 · 배포 → 점검.
