# Backend — FastAPI + Supabase(PostgreSQL)

## 처음 한 번 (backend 폴더에서)

```bash
cp .env.example .env              # Windows: copy .env.example .env → 값 채우기 (커밋 금지)
uv sync                           # Python 3.12 + 패키지 설치
uv run python -m app.db.init_db   # 내 스키마(hotel_<이름>)를 지우고 팀 DDL + 개발용 데이터로 다시 만듦
```

- DB는 **Supabase(PostgreSQL) 팀 프로젝트 하나를 5명이 같이** 씁니다. 비밀번호는 팀 채팅으로만 주고받습니다(저장소 · 노션 금지).
- `.env`의 `DATABASE_URL`에는 프로젝트 → Connect → **Session pooler** URI를 넣습니다(Direct connection은 IPv6 전용이라 안 될 수 있음).
- 서로의 데이터를 지우지 않도록 **스키마로 나눕니다.**

  | 용도 | `DB_SCHEMA` | 지우고 다시 만들기 |
  |---|---|---|
  | 각자 개발 | `hotel_<영문 이름>` (예: `hotel_minhyuk`) | `init_db`로 언제든 (`DB_RESET_ALLOWED=true`) |
  | 각자 테스트 | 자동으로 `hotel_<이름>_test` | 테스트가 매번 |
  | 시연 · 통합 확인 | `hotel` (공용) | 팀에 알리고 `--reset-shared`를 붙였을 때만 |
- 열쇠(비밀번호)는 하나라서 남의 스키마도 기술적으로는 열립니다. **남의 스키마와 `hotel`은 지우거나 고치지 않는 것**이 규칙입니다.
- 무료 플랜은 동시 연결 수가 적어서 서버 하나가 연결을 최대 5개만 씁니다.

## 실행 · 테스트

```bash
uv run fastapi dev app/main.py --port 8000   # http://localhost:8000/docs
uv run pytest                                # hotel_<이름>_test 스키마를 새로 만들어 테스트
```

- DB 연결 확인: http://localhost:8000/api/health/db
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
│   └── dev_seed.sql        화면설계서 12월 예시와 같은 가상 데이터
├── models/                 테이블 1개 = 파일 1개 (member, room, reservation, closed_date, attach_file, menu)
├── schemas/                요청/응답 Pydantic 모델 (JSON 은 camelCase)
├── services/               비즈니스 로직 (room_service: 추천 점수 · 예약 가능 여부)
└── api/
    ├── deps.py             DB, CurrentMember, AdminMember 의존성
    ├── router.py           라우터 모음
    └── routes/
        ├── health.py · members.py · menus.py · rooms.py · reservations.py · files.py
        └── admin/          rooms.py (ADM-001) · closed_dates.py (ADM-002) · reservations.py (ADM-003)
tests/                      pytest (conftest.py 의 empty_db / seeded_db 픽스처)
```

테이블 정의는 저장소의 `docs/hotel_reservation_ddl.sql` 하나가 기준입니다. 전체 구조 그림은 `docs/ARCHITECTURE.md`.

## 규칙

- 모든 API 는 `/api` 접두사. 에러는 `{"detail": {"code", "message"}}`.
- 로그인 필요: `member: CurrentMember`, 관리자 전용: `dependencies=[Depends(require_admin)]`.
- 테이블은 DDL로 만들므로 `create_all` 을 쓰지 않습니다. 스키마를 바꾸면 `docs/hotel_reservation_ddl.sql`을 고치고 모델도 맞춥니다.
- `reservation.updated_at` 은 상태 변경 코드에서 직접 갱신합니다.
- 예약이 차지하는 날은 `체크인 ≤ 날짜 < 체크아웃`, 살아 있는 예약은 `PENDING`·`APPROVED` (`models/reservation.py`의 `LIVE_STATUSES`).
- 비밀번호는 `scrypt$salt$hash` 형식. 로그인 · 비밀번호 확인을 5번 틀리면 10분 잠금(429, 서버 메모리).
