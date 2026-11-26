# FINAL_CHECKLIST — 최종 완료 체크리스트

- 제출 마감: **11-26(목) 10:00** (11-25 수요일 종료 전 초안). 발표 11-26 14:30.
- 기능 동결: 11-25(수) 오후 → `dev` → `main` PR 한 번.
- 체크는 확인한 사람이 하고, 옆에 날짜를 적습니다. (11-24 기준으로 확인된 것만 체크, 11-25 Step 3 반영분은 날짜 표시)
- 기준: main `070a8b5`, 2026-11-26 (배포 · #107~#114 반영, 테스트 200개). 11-26 체크는 RELEASE_TEST 7절 · 배포 확인 · pytest 200 통과 근거. 직전 판: [docs/archive/2026-11-25_step3/DevelopDoc/FINAL_CHECKLIST.md](../docs/archive/2026-11-25_step3/DevelopDoc/FINAL_CHECKLIST.md) · 그 전 판: [docs/archive/2026-11-25_step2/DevelopDoc/FINAL_CHECKLIST.md](../docs/archive/2026-11-25_step2/DevelopDoc/FINAL_CHECKLIST.md)

## 1. 제출물

- [x] GitHub 저장소 링크 (`hotel-sol/Hotel-reservation`)
- [x] 저장소 최상단 `README.md`: 서비스 소개 · 실행 방법 · 시연 주소 (11-26)
- [x] `DevelopDoc/PRD.md` 제품 요구사항
- [x] `DevelopDoc/TECH_SPEC.md` 기술 명세
- [x] `DevelopDoc/WORK_UNITS.md` 작업 단위 · 완료 조건
- [ ] `DevelopDoc/FINAL_CHECKLIST.md` (이 문서) 모든 필수 항목 체크 — 11-26 기준 남은 것: 발표 직전 Supabase 상태 확인, 해커톤 뒤 비밀번호 교체
- [x] 시연 · 체험할 수 있는 URL 또는 실행 방법 — 화면 https://hotel-reservation-ten-phi.vercel.app · API https://hotel-sol-api.onrender.com (11-26)
- [x] 발표 자료 (역할 분담 · 개발 일정 포함, 객실 사진은 AI 생성이라고 표기) — [docs/presentation/0_team_발표자료_최종.pdf](../docs/presentation/0_team_발표자료_최종.pdf) (11-26)

## 2. 기능 — 시연 시나리오가 끝까지 동작

- [x] 손님 가입 → 로그인 (11-25, RELEASE_TEST 7절 M1 · M2)
- [x] 객실 추천: 날짜 · 인원 입력 → 예약 가능한 객실만, 추천순 · 인기순 · 가격순, 1~3위 "★ 추천" · HOT · NEW, 대표 사진 (11-25, G1 · G2)
- [x] 예약 신청 → 완료 화면 → 내 예약에 "대기" (11-25, M5 · M6)
- [x] 관리자 로그인 → 예약 관리에서 승인 → 손님 내 예약이 "승인" (11-25, A1 · A10)
- [x] 관리자 휴무 지정(호텔 전체 · 객실별 · 기간, 사유 분류) → 그 날짜가 추천에서 빠지고 예약은 409, 휴무 묶음 목록에 예정 · 진행 중 · 종료 표시 (11-25, A6~A9)
- [x] 관리자 객실 관리: 추가 · 수정 · 비활성 · 사진 올리기, 요약 카드 숫자 (11-25, A2~A5. 추가는 공용 데이터를 지키려 화면 테스트에서 빼고 자동 테스트로 확인)
- [x] 예약 달력에서 막힌 날짜 비활성 (이슈 #27 닫힘, PR #54 · #71)

- [x] 실제 화면 테스트 한 바퀴: [RELEASE_TEST](RELEASE_TEST.md) (공용 `hotel`, 11-25 main `5e9d871`)

## 3. 품질

- [x] `backend`: `uv run pytest` 전부 통과 (11-26, main `070a8b5`, 200개. 11-24에는 77개)
- [x] `frontend`: `npx tsc --noEmit` · `npm run lint` 오류 0 (11-24)
- [x] `frontend`: `npm run build` 통과 (11-25 main 최종 테스트, 이후 Vercel 배포 빌드 성공)
- [x] 브라우저 콘솔 · 서버 로그에 오류 없음 (11-25, RELEASE_TEST 7절 C3: 서버 500 0건 · 콘솔 오류 0건)
- [x] 화면에 영어 오류 · 빈 화면 없음 (오류는 한국어 `message`) (11-25, C3)

## 4. 데이터 · DB

- [x] 공용 `hotel` 스키마에 시연 데이터 (11-25 완료): 팀에 알린 뒤 `uv run python -m app.db.init_db --demo --reset-shared`
- [x] 공용 관리자 `admin01` 로그인 확인(비밀번호는 팀 채팅) (11-25, A1)
- [x] DB 시간대 `Asia/Seoul` (11-24)
- [x] 팀 Supabase에 `btree_gist` 확장(`extensions` 스키마) 켜 둠 — 이중 예약 제약에 필요 (11-25)
- [x] 공용 `hotel` 스키마를 Step 3 DDL(테이블 10개)로 다시 만듦 — 11-25 완료(객실 40 · 사진 142 · admin01 · 이중 예약 제약 확인, #60 공지)
- [ ] 발표 직전 Supabase 대시보드에서 프로젝트 상태 확인(무료 플랜은 7일 접속이 없으면 일시 정지)

## 5. 보안

- [x] `.env` · 비밀번호 · 키가 저장소에 없음 (`.env.example`만)
- [x] 관리자 API는 로그인 안 됨 401 · 관리자 아님 403 (테스트)
- [x] 비밀번호 scrypt 해시, 5번 틀리면 10분 잠금 (11-25부터 `login_attempt` 테이블에 기록)
- [x] 비밀번호 찾기는 시연 전까지 꺼 둠 — API 403, 화면은 안내만 (11-25, 보안 #67)
- [x] 이중 예약은 DB 제약(`EXCLUDE`)으로도 막음, 승인 대기 예약은 회원당 최대 3건 (11-25)
- [x] 배포하면 HTTPS (로그인 쿠키가 Secure) — Vercel · Render 모두 HTTPS (11-25)
- [x] 배포 서버 `APP_ENV=production` + 32자 이상 무작위 `SESSION_SECRET` (아니면 서버가 안 켜짐, #70) — Render 설정, 서버 정상 기동 (11-25)
- [x] `health/db`가 DB 버전을 보여 주지 않음 (#70, PR #94)
- [ ] 해커톤 끝나면 DB 비밀번호와 `admin01` 비밀번호 교체 (대화 · 노션 기록에 노출된 적 있음)

## 6. 저장소 정리

- [x] `dev` → `main` PR로만 반영, 11-23 Git Flow 도입 뒤 `main`에 직접 올린 커밋 없음 (11-26 확인)
- [x] 열린 PR 0 · 열린 이슈 0 (11-26 확인)
- [ ] (선택) 보호 규칙 다시 적용 — 팀장이 보관한 백업 JSON으로 Import
- [x] 과거 설계 자료는 `docs/archive/`, 지금 기준 문서는 `DevelopDoc/` · `docs/ARCHITECTURE.md`
