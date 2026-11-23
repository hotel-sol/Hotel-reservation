# 태양의 호텔 — 호텔 예약 시스템

손님은 객실을 추천받아 예약하고, 관리자는 객실 · 휴무일 · 예약을 관리합니다. 3기 바이브코딩 해커톤(11-19 ~ 11-26).

| 폴더 | 내용 |
|---|---|
| [`frontend/`](frontend/README.md) | Next.js 화면 (:3000). `/api/*`를 백엔드로 넘김 |
| [`backend/`](backend/README.md) | FastAPI + SQLAlchemy (:8000). DB는 Supabase(PostgreSQL) 팀 프로젝트 하나, 개발은 각자 스키마 hotel_<이름> |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | **전체 구조 · ERD · 예약 흐름 · 상태 · 화면별 API 현황 (그림)** |
| [`docs/README.md`](docs/README.md) | DB 설계 · 화면 설계서 (1~5번) |
| [`docs/hotel_reservation_ddl.sql`](docs/hotel_reservation_ddl.sql) | 테이블 정의 (기준) |

## 실행 (백엔드 먼저)

```bash
# 1) 백엔드 — backend 폴더
cp .env.example .env                 # 값 채우기 (커밋 금지)
uv sync
uv run python -m app.db.init_db      # 내 스키마(hotel_<이름>)에 테이블 · 개발용 데이터 생성
uv run fastapi dev app/main.py --port 8000

# 2) 프론트 — frontend 폴더
cp .env.example .env.local
npm install
npm run dev                          # http://localhost:3000
```
