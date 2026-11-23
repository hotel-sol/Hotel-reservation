# Backend — FastAPI + MSSQL

## 실행

```bash
cp .env.example .env    # DB_HOST / DB_NAME / DB_USER / DB_PASSWORD / SESSION_SECRET
uv sync
uv run fastapi dev app/main.py --port 8000
```

- Swagger: http://localhost:8000/docs
- DB 연결 확인: http://localhost:8000/api/health/db
- 테스트: `uv run pytest`

Python 3.12 (`.python-version`). DB 드라이버는 `pymssql` 이라 ODBC 드라이버 설치가 필요 없습니다.

## 구조

```
app/
├── main.py                 FastAPI 앱, CORS, /api 라우터 등록
├── core/
│   ├── config.py           .env → Settings (DB URL 조립)
│   ├── security.py         비밀번호 scrypt 해시, 세션 쿠키 서명
│   └── exceptions.py       fail(status, code, message) 공통 에러
├── db/
│   ├── base.py             SQLAlchemy DeclarativeBase
│   └── session.py          engine, get_db()
├── models/                 테이블 1개 = 파일 1개 (member, room, reservation, closed_date, attach_file, menu)
├── schemas/                요청/응답 Pydantic 모델 (JSON 은 camelCase)
├── services/               비즈니스 로직 (room_service: 추천 점수 · 예약 가능 여부)
└── api/
    ├── deps.py             DB, CurrentMember, AdminMember 의존성
    ├── router.py           라우터 모음
    └── routes/
        ├── health.py · members.py · menus.py · rooms.py · reservations.py · files.py
        └── admin/          rooms.py (ADM-001) · closed_dates.py (ADM-002) · reservations.py (ADM-003)
sql/mssql_ddl.sql           참고 저장소 MySQL DDL 을 MSSQL 로 옮긴 것 (개발 DB 에는 이미 생성됨)
tests/                      pytest
```

## 규칙

- 모든 API 는 `/api` 접두사. 에러는 `{"detail": {"code", "message"}}`.
- 로그인 필요: `member: CurrentMember`, 관리자 전용: `dependencies=[Depends(require_admin)]`.
- 테이블은 DB 에 이미 있으므로 `create_all` 을 쓰지 않습니다. 스키마 변경은 `sql/` 에 SQL 로 남기세요.
- MSSQL 은 `ON UPDATE` 가 없어서 `reservation.updated_at` 은 상태 변경 코드에서 직접 갱신합니다.
- 비밀번호 해시는 참고 저장소와 같은 `scrypt$salt$hash` 형식입니다.
