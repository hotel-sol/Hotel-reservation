# 개발 진행 정리 — 최웅식 (2026-11-23)

> 담당: **5. 공통 · 예약 관리 (ADM-003)**, frontend 전반 연동
> 작업 브랜치: **`feature/woochoi-01`** (dev 에서 만듦. 앞으로 이 브랜치 하나만 사용)
> 개인 개발 정리 파일입니다. 저장소가 공개라서 비밀번호 같은 접속 정보는 적지 않습니다.

---

## 1. 지금 상태 한눈에

| 항목 | 상태 |
|---|---|
| 작업 브랜치 | `feature/woochoi-01` — 커밋 · push 완료 (`bc9e7c1`), **dev 로 PR 아직 안 만듦** |
| GitHub `dev` | `a6e2507` (PR #26까지). 내 브랜치보다 앞서 있음 → 내일 `origin/dev` 를 내 브랜치에 머지할 것 |
| GitHub `main` | `b3d2528` (PR #25: 예약 일자 관리 Step 2 릴리스) |
| DB | 팀 Supabase 프로젝트, 내 스키마 **`hotel_woongsik`** (공용 `hotel` 아님) |
| 백엔드 테스트 | 52개 모두 통과 (`hotel_woongsik_test` 스키마) |
| 실행 중 서버 | 프론트 3000, 백엔드 8000 (개발 모드) |

---

## 2. 오늘 한 일 (시간 순)

### 2-1. frontend 최신 문법 검토 (context7 문서 기준)
- Next.js 16.4 / React 19 / Tailwind v4 문서와 비교 → 구조 · 설정은 최신.
- 고친 것 (`eb60628`, main 직접 push — 브랜치 규칙 생기기 전)
  - `useEffect` 데이터 로딩 6곳에 `ignore` 처리 (늦게 온 응답이 화면을 덮어쓰지 않게)
  - Tailwind 연결을 `@tailwindcss/turbopack` → 공식 문서 방식 `@tailwindcss/postcss` + `postcss.config.mjs`
  - react 19.3.1, tailwindcss 4.3.5 로 패치 업데이트

### 2-2. 백엔드 변경(Supabase 전환)에 frontend 맞춤 — PR #14 (dev 머지됨)
- 예약 일자 관리(ADM-002) 달력 화면: 객실 선택 · 월 이동 · 휴무/예약 수 · 지정/해제 · 이번 달 목록
- 마이페이지: 정보 수정 · 비밀번호 변경 · 탈퇴, `/password-reset` 비밀번호 찾기
- API 함수 · 타입을 새 회원 · 휴무일 API에 맞춤

### 2-3. 객실 추천 카드 — PR #20 (dev 머지됨)
- ROOM-001 설계서 카드: 대표 사진(없으면 아이콘), "추천" 표시, `1박 요금 · 최대 인원`, `조회 N · 예약 N`
- `/uploads/*` 프록시, `fileUrl()` 추가 (백엔드가 `/uploads` 를 정적 파일로 내줘야 사진이 보임)

### 2-4. 휴무 기간 지정(3A) 화면 — PR #24 (닫힘)
- 팀원 PR #22(3B) · #23(3C)에 같은 기능이 먼저 들어가서 닫음.
- 로컬 dev 에서 섞이며 빌드가 깨진 것을 팀원 버전으로 되돌려 정리 (`8fb4270`).

### 2-5. Supabase 연동 테스트 (내 스키마 `hotel_woongsik`)
- `backend/.env` 작성(git 제외 확인), `init_db` 로 스키마 생성, `pytest` 통과
- 브라우저 연동: 회원가입 → 로그인 → 객실 검색(예약된 방 제외) → 예약 → 완료 → 내 예약 → 마이페이지 → 관리자 승인 → 휴무 지정(기간 · 사유) → 휴무일 검색 차단까지 모두 정상

### 2-6. 관리자 예약 관리(ADM-003) 설계서 맞춤 — `feature/woochoi-01` (`bc9e7c1`)
**백엔드** (`backend/app/api/routes/admin/reservations.py`)
- `GET /api/admin/reservations/counts` 추가 — 상태별 건수 `{ALL, PENDING, APPROVED, CANCELED}`, 검색 조건은 목록과 같음
- 취소 가능 판단 `date.today()` → `today_kst()`
- `updated_at` 을 `datetime.now()` → DB `now()` (created_at 과 같은 시계, 9시간 차이 문제 해결)
- 상태 오류 문구 한글화: "이미 취소 상태인 예약이라 승인할 수 없습니다."
- 테스트 `backend/tests/test_admin_reservations.py` 9개 추가

**프론트** (`frontend/src/app/admin/reservations/ReservationManager.tsx`)
- 탭 옆 건수 (전체 / 승인 대기 / 승인 / 취소)
- `confirm()` 대신 화면 안 확인 팝업(④): 예약 내용 · 요청 사항, 닫기 / 승인하기 · 취소하기, Esc 로 닫기
- 오류는 팝업 안에 표시, 닫으면 목록 · 건수 다시 불러옴
- 체크인이 지난 예약은 취소 버튼 대신 "-"
- 표 머리글 설계서대로 (예약 번호 · 숙박 기간 · 관리)

브라우저 확인: 탭 건수, 검색(기간 · 이름 · 번호), 페이지, 승인 · 취소 팝업, 지난 체크인, 동시 변경 시 오류 안내 모두 정상.

---

## 3. 내 PR 기록

| PR | 내용 | 상태 |
|---|---|---|
| #14 | 바뀐 백엔드 API에 맞춰 예약 일자 관리 달력 · 마이페이지 · 비밀번호 찾기 | dev 머지 |
| #15 | 로컬 실행 설정 · .DS_Store 무시 (→ main) | 닫힘 (나중에 dev 를 main 에 직접 머지하며 반영) |
| #17 | feature/frontend-api-sync → main | 닫힘 |
| #19 | (main → dev) | 닫힘 |
| #20 | 객실 추천 카드 ROOM-001 맞춤 | dev 머지 |
| #24 | 휴무 기간 지정(3A) 화면 | 닫힘 (팀원 #22와 중복) |

---

## 4. 개발 환경 메모

```bash
# 백엔드 (backend 폴더)
uv run fastapi dev app/main.py --port 8000   # http://localhost:8000/docs
uv run pytest                                # hotel_woongsik_test 스키마로 테스트
uv run python -m app.db.init_db              # 내 스키마를 시드 데이터로 다시 만들기

# 프론트 (frontend 폴더)
npm run dev                                  # http://localhost:3000
npm run lint && npm run build                # PR 전에 통과해야 함
```

- `backend/.env`: `DB_SCHEMA=hotel_woongsik`, `DB_RESET_ALLOWED=true` (접속 주소 · 비밀번호는 팀 채팅 참고, 커밋 금지)
- 관리자 로그인: `admin01` (비밀번호는 `.env` 의 `ADMIN_PASSWORD`). **5번 틀리면 10분 잠금** → 백엔드를 다시 켜면 풀림
- 테스트 손님 계정: `zz_e2e_woongsik` (비밀번호는 `.env` 의 `TEST_PASSWORD`, 내 스키마에만 있음)
- DataGrip: Host `aws-1-ap-northeast-1.pooler.supabase.com`, Port 5432, DB `postgres`, SSL require, Schemas 에서 `hotel_woongsik` 선택. Single session mode · Read-only 추천
- 브랜치 규칙: `feature/woochoi-01` 하나만 사용 → PR 은 `dev` 로. main · dev 직접 push 하지 않기

---

## 5. 다음에 할 일

1. **`origin/dev` 를 `feature/woochoi-01` 에 머지** (dev 가 #25 · #26 으로 앞서 있음) → 빌드 · 테스트
2. **`feature/woochoi-01` → `dev` PR 만들기** (ADM-003 개선분)
3. 관리자 화면 상단 메뉴에 손님 메뉴(객실 추천 · 내 예약)도 같이 나옴 → 설계서는 관리자 메뉴만. 백엔드 `/menus` 확인 필요 (파트 5 범위)
4. 객실 사진: 백엔드 `/uploads` 정적 파일 제공 + `POST /files` 업로드(현재 501) — 팀과 담당 정하기
5. 테스트 데이터 정리: 내 스키마의 테스트 예약 · 휴무는 `init_db` 로 초기화 가능
