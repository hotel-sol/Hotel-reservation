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

## 브랜치 규칙 (Git Flow 간소화, 11-23)

이틀짜리 해커톤이라 `release/*` · `hotfix/*`는 쓰지 않고 세 가지만 씁니다.

| 브랜치 | 용도 | 어디서 만들고 어디로 합치나 |
|---|---|---|
| `main` | 제출 · 시연 버전 | 11-25 기능 동결 때 `dev` → `main` PR 한 번 |
| `dev` | 팀 통합 개발 | 모든 기능 PR이 여기로 |
| `feature/<파트>-<내용>` | 각자 작업 (예: `feature/roomdate-calendar`) | `dev`에서 만들고 `dev`로 PR |

```bash
git switch dev && git pull                     # 항상 최신 dev에서 시작
git switch -c feature/roomdate-calendar        # 내 작업 브랜치
# ... 작업 · 커밋 ...
git push -u origin feature/roomdate-calendar
gh pr create --base dev                        # PR은 dev로 (main 아님)
```

- **main · dev에 직접 push할 수 없습니다**(저장소 규칙). 모든 변경은 PR로 합칩니다.
- **PR은 본인이 만들고 본인이 합쳐도 됩니다**(승인 0명). 다른 사람에게 봐 달라고 하고 싶으면 리뷰를 요청하세요.
- **main으로 가는 PR은 `dev`에서만** 됩니다. 다른 브랜치에서 main으로 PR을 열면 `main-from-dev-only` 검사(`.github/workflows/main-from-dev.yml`)가 실패해서 합칠 수 없습니다. 이때는 PR 화면에서 base를 `dev`로 바꾸면 됩니다.
- PR 전에 `backend`에서 `uv run pytest`, `frontend`에서 `npm run build`가 통과해야 합니다.
- 오래 걸리는 작업이면 중간에 `git pull origin dev`로 최신 dev를 받아 충돌을 일찍 풉니다.

지켜지는지 확인하기:

```bash
git fetch --prune && git branch -r                          # origin/dev, origin/feature/... 가 보이는지
gh pr list --base dev                                       # dev로 간 PR
gh pr list --base main --state all                          # main으로 간 PR (동결 때 1건만이어야 함)
git log origin/main --first-parent --no-merges --oneline    # main에 PR 없이 올라간 커밋 (11-23 이전 것 외에 새로 생기면 안 됨)
git log --graph --oneline --all -30                         # 브랜치 모양 (GitHub: Insights → Network)
```
