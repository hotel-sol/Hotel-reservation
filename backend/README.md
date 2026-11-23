# Backend — FastAPI + MariaDB

## 처음 한 번 (backend 폴더에서)

```bash
cp .env.example .env              # Windows: copy .env.example .env → 값 채우기 (커밋 금지)
uv sync                           # Python 3.12 + 패키지 설치
uv run python -m app.db.init_db   # 로컬 DB(hotel)를 지우고 팀 DDL + 개발용 데이터로 다시 만듦
```

- 개발 DB는 **각자 PC의 MariaDB**입니다. 시연 DB는 아직 정하지 않았고, 정해지면 `.env` 값만 바꿉니다.
- `init_db`는 DB를 지우므로 `DB_HOST`가 `127.0.0.1` · `localhost`일 때만 실행됩니다.
- `.env`에 `ADMIN_PASSWORD`(팀 채팅으로 받음)를 넣고 `init_db`를 실행하면 팀 공용 관리자 `admin01`이 생깁니다. 다른 관리자는 `uv run python -m app.db.create_admin <아이디> <이름>`.

## 실행 · 테스트

```bash
uv run fastapi dev app/main.py --port 8000   # http://localhost:8000/docs
uv run pytest                                # hotel_test DB를 새로 만들어 테스트 (로컬 MariaDB 필요)
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
│   ├── init_db.py          로컬 DB 다시 만들기 (팀 DDL + dev_seed.sql)
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
