# 태양의 호텔 — 호텔 예약 시스템

손님은 날짜와 인원만 넣으면 **예약 가능한 객실을 추천받아 바로 예약**하고, 관리자는 **객실 · 휴무일 · 예약 승인**을 관리하는 호텔 예약 서비스입니다. 3기 바이브코딩 해커톤(11-19 ~ 11-26), 5인 팀.

## 시연 주소

| 무엇 | 주소 |
|---|---|
| 화면 (Vercel) | https://hotel-reservation-ten-phi.vercel.app |
| 백엔드 API (Render) | https://hotel-sol-api.onrender.com (상태 확인 `/api/health/db`) |

- `main`에 push하면 둘 다 자동으로 다시 배포됩니다. DB는 Supabase 공용 `hotel` 스키마(객실 40개, 사진은 AI 생성).
- Render 무료 플랜은 15분 동안 요청이 없으면 잠들어 첫 응답이 30초~1분 걸립니다. 시연 전에 위 상태 확인 주소를 한 번 열어 깨워 두세요.
- 손님 기능은 가입 후 바로 쓸 수 있습니다. 관리자 계정은 팀에 문의(비밀번호는 저장소에 두지 않음).
- 발표 자료: [docs/presentation/0_team_발표자료_최종.pdf](docs/presentation/0_team_발표자료_최종.pdf)

- 기준: main `070a8b5`, 2026-11-26 (배포 · #107~#114 반영, 테스트 200개). 직전 판: [docs/archive/2026-11-25_step3/ROOT_README.md](docs/archive/2026-11-25_step3/ROOT_README.md) · 그 전 판: [docs/archive/2026-11-25_step2/ROOT_README.md](docs/archive/2026-11-25_step2/ROOT_README.md)

## 무엇을 할 수 있나

| 누가 | 화면 | 기능 |
|---|---|---|
| 손님 | 객실 추천 `/rooms` | 날짜 · 인원으로 예약 가능한 객실만 보기, 추천순(조회 40 · 최근 30일 승인 예약 60 점수) · 인기순 · 가격순, 대표 사진, 객실 상세 |
| 손님 | 예약 `/reservation/new` → 완료 → 내 예약 | 예약 신청(인원 · 휴무 · 겹침을 서버가 검사, 금액 자동 계산, 최대 6박 · 30일 안, 승인 대기 최대 3건), 상태 확인. 취소는 관리자만 |
| 손님 | 회원 `/signup` `/login` `/mypage` `/password-reset` | 가입 · 로그인 · 내 정보 · 비밀번호 변경 · 탈퇴. 비밀번호 찾기는 시연 전까지 꺼 둠(안내만) |
| 관리자 | 객실 관리 `/admin/rooms` | 객실 추가 · 수정 · 비활성, 등급(S · A · B · C) · 전망, 사진(최대 5장), 요약 카드(판매 중 · 오늘 휴무 · 휴무 예정) |
| 관리자 | 예약 일자 관리 `/admin/closed-dates` | 달력에서 호텔 전체 / 객실별 휴무 지정 · 해제, 기간(최대 31일) · Shift+클릭, 남은 객실 수, 사유 분류, 휴무 묶음 목록(예정 · 진행 중 · 종료) |
| 관리자 | 예약 관리 `/admin/reservations` | 상태 · 기간 · 검색, 승인 · 취소 |

휴무로 지정한 날은 추천에서 빠지고 예약도 막힙니다. 체크아웃 날은 다음 손님이 체크인할 수 있습니다. 같은 방 이중 예약은 DB 제약으로도 막습니다.

**기술:** Next.js 16 · React 19 · Tailwind CSS / FastAPI · SQLAlchemy 2 (Python 3.12) / Supabase PostgreSQL

## 문서

| 위치 | 내용 |
|---|---|
| [`DevelopDoc/`](DevelopDoc/) | **개발 문서**: [PRD](DevelopDoc/PRD.md) · [TECH_SPEC](DevelopDoc/TECH_SPEC.md) · [WORK_UNITS](DevelopDoc/WORK_UNITS.md) · [FINAL_CHECKLIST](DevelopDoc/FINAL_CHECKLIST.md) |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 전체 구조 · ERD · 예약 흐름 · 상태 · 휴무 지정 · 로그인 · 화면별 API 현황 (그림) |
| [`docs/hotel_reservation_ddl.sql`](docs/hotel_reservation_ddl.sql) | 테이블 정의 (기준, 10개) |
| [`docs/archive/`](docs/archive/) | 과거 자료: 11-19~11-23 설계서 · ERD · 화면 설계 그림, [Step 3 반영 직후 문서](docs/archive/2026-11-25_step3/README.md) · [Step 3 반영 전 문서](docs/archive/2026-11-25_step2/) |
| [`frontend/`](frontend/README.md) | Next.js 화면 (:3000). `/api/*`를 백엔드로 넘김 |
| [`backend/`](backend/README.md) | FastAPI (:8000). DB는 Supabase 팀 프로젝트 하나, 개발은 각자 스키마 `hotel_<이름>` |

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

- **main · dev에 직접 push하지 않습니다.** 모든 변경은 PR로 합칩니다.
- PR 전에 `backend`에서 `uv run pytest`, `frontend`에서 `npm run build`가 통과해야 합니다.
- 오래 걸리는 작업이면 중간에 `git pull origin dev`로 최신 dev를 받아 충돌을 일찍 풉니다.
- 작업 브랜치 이름은 `feature/*` 외에 `fix/*` · `db/*` · `docs/*`도 씁니다(모두 `dev`에서 만들고 `dev`로 PR).
- 팀 규칙 R1~R8은 GitHub Discussion #60에 있습니다. DB 파일(DDL · 시드 · `tests/conftest.py` · `tests/helpers.py`)은 DB 담당이 고치고, 테스트 데이터는 `tests/helpers.py`로만 넣습니다.

지켜지는지 확인하기:

```bash
git fetch --prune && git branch -r                          # origin/dev, origin/feature/... 가 보이는지
gh pr list --base dev                                       # dev로 간 PR
gh pr list --base main --state all                          # main으로 간 PR (동결 때 1건만이어야 함)
git log origin/main --first-parent --no-merges --oneline    # main에 PR 없이 올라간 커밋 (11-23 이전 것 외에 새로 생기면 안 됨)
git log --graph --oneline --all -30                         # 브랜치 모양 (GitHub: Insights → Network)
```
