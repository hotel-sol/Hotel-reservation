# 태양의 호텔 — 시스템 구조 한눈에 보기

GitHub에서 그림(Mermaid)으로 보입니다. 기준: **dev `251bf9c`, 2026-11-25 (Step 3 반영)**(Step 1 + Step 2 + Step 3-A, PR #83까지). 이전 판: [archive/2026-11-25_step2/docs/ARCHITECTURE.md](archive/2026-11-25_step2/docs/ARCHITECTURE.md). DB는 Supabase(PostgreSQL) 팀 프로젝트 하나: 각자 개발은 스키마 hotel_<이름>, 테스트는 hotel_<이름>_test, 시연은 공용 스키마 hotel. DB 시간대는 `Asia/Seoul`(11-24부터).

제품 요구사항 · 기술 명세 · 작업 단위는 [`../DevelopDoc/`](../DevelopDoc/)에 있습니다.

## 1. 전체 구조

```mermaid
flowchart LR
    U["브라우저<br/>(손님 · 관리자)"]
    subgraph FE["frontend/ — Next.js :3000"]
        P["화면(app/)<br/>/rooms · /reservation · /admin/..."]
        RW["rewrites<br/>/api/* → :8000/api/*"]
    end
    subgraph BE["backend/ — FastAPI :8000"]
        R["routes<br/>(/api/...)"]
        S["services<br/>추천 점수 · 빈방 판정 · 예약 확인/요금 · 사진 저장"]
        M["models<br/>(SQLAlchemy)"]
    end
    DB[("Supabase PostgreSQL<br/>스키마 hotel")]
    ST[("Supabase Storage<br/>버킷 room-photos")]

    U -- "화면 요청" --> P
    U -- "API 호출 /api/* + 로그인 쿠키" --> RW
    RW --> R
    R --> S --> M
    R --> M
    M --> DB
    S -.->|"SUPABASE_URL 있을 때만<br/>(없으면 backend/uploads/)"| ST
```

- 브라우저는 `localhost:3000` 한 주소만 봅니다. 그래서 로그인 쿠키(HttpOnly, SameSite=Lax)가 그대로 동작하고 CORS 설정이 필요 없습니다.
- DDL: `docs/hotel_reservation_ddl.sql`. 개발 DB 만들기: `backend`에서 `uv run python -m app.db.init_db`(내 스키마 `hotel_<이름>`에만. 공용 `hotel`은 `--reset-shared`가 있어야 지워짐).
- 이중 예약 제약에 쓰는 `btree_gist` 확장은 팀 Supabase에 `extensions` 스키마로 켜 둠(DDL에는 없음).
- 주소에 DB 숫자 범위를 넘는 번호가 오면 500 대신 404(`main.py`, 모든 API 공통).

## 2. DB 구조 (ERD, 테이블 10개)

```mermaid
erDiagram
    MEMBER ||--o{ RESERVATION : "예약한다"
    MEMBER |o--o{ RESERVATION : "취소한 관리자 (canceled_by)"
    MEMBER |o--o{ CLOSURE : "지정한 관리자 (created_by)"
    ROOM_GRADE |o--o{ ROOM : "등급"
    ROOM ||--o{ RESERVATION : "예약된다"
    ROOM ||--o{ ROOM_VIEW : "조회 기록"
    ROOM |o--o{ CLOSED_DATE : "쉬는 날 (room_id NULL = 호텔 전체)"
    CLOSURE ||--|{ CLOSED_DATE : "휴무 묶음 (지우면 날짜도 삭제)"
    ROOM ||--o{ ATTACH_FILE : "사진 (target_type='ROOM')"
    MENU |o--o{ MENU : "상위 메뉴"

    MEMBER {
        bigint member_id PK
        varchar login_id UK "대소문자 무시, 탈퇴하면 withdrawn-N"
        varchar password "scrypt$salt$hash"
        varchar name
        varchar phone
        varchar email UK
        varchar role "USER / ADMIN"
        datetime created_at
    }
    LOGIN_ATTEMPT {
        varchar attempt_key "login:아이디 / device:번호:기기 / password:번호"
        datetime failed_at "최근 10분 5번이면 잠금"
    }
    ROOM_GRADE {
        bigint grade_id PK
        char grade_code UK "S / A / B / C"
        varchar grade_name UK "로얄 스위트 / 이그제큐티브 스위트 / 프리미어 / 디럭스"
        int base_price
        int base_guest "S 4, A · B · C 2"
        int max_guest
        int area_m2
        varchar bed_type
    }
    ROOM {
        bigint room_id PK
        varchar room_name UK
        varchar room_type
        int max_guest "1 ~ 20"
        int price "1박 요금, 1 ~ 10,000,000"
        varchar description
        int view_count "추천 점수에 사용"
        char is_active "Y / N (삭제 대신 비활성화)"
        bigint grade_id FK
        varchar view_type "RIVER / CITY / MOUNTAIN"
        varchar bed_type
        datetime created_at
    }
    ROOM_VIEW {
        bigint room_id PK
        varchar viewer_key PK "회원 M:번호 / 비회원 G"
        date view_date PK "한국 날짜"
    }
    RESERVATION {
        bigint reservation_id PK
        bigint member_id FK
        bigint room_id FK
        date check_in_date
        date check_out_date "체크인보다 뒤"
        int guest_count
        int price_per_night "예약 때 1박 요금"
        int total_price "1박 요금 x 숙박일수"
        varchar status "PENDING / APPROVED / CANCELED"
        varchar request_memo "최대 200자"
        datetime canceled_at "CANCELED 일 때만"
        bigint canceled_by FK
        varchar cancel_reason
        datetime created_at
        datetime updated_at "상태 바뀐 시각"
    }
    CLOSURE {
        bigint closure_id PK
        varchar reason_code "CONSTRUCTION / MAINTENANCE / EVENT / CLOSURE / ETC"
        varchar reason "상세 사유"
        bigint created_by FK
        datetime created_at
    }
    CLOSED_DATE {
        bigint closed_date_id PK
        bigint room_id FK "NULL = 호텔 전체 휴무"
        date closed_date
        bigint closure_id FK "NOT NULL"
        datetime created_at
    }
    ATTACH_FILE {
        bigint file_id PK
        varchar target_type "예: ROOM"
        bigint target_id "그 대상의 번호"
        varchar original_name
        varchar saved_path "uploads/... / Storage 공개 주소 / room-photos/..."
        bigint file_size
        datetime created_at
    }
    MENU {
        bigint menu_id PK
        bigint parent_id FK
        varchar menu_name
        varchar menu_url
        varchar role "USER / ADMIN"
        int sort_order
        char is_used "Y / N"
    }
```

- `reservation` 제약: `ck_reservation_canceled`(`CANCELED` ↔ `canceled_at` 있음), `ex_reservation_no_overlap`(살아 있는 예약끼리 같은 방 `[체크인, 체크아웃)` 겹침 금지, `EXCLUDE USING gist`). 인덱스는 `idx_reservation_member`, `idx_reservation_live`.
- `closed_date`: `UNIQUE NULLS NOT DISTINCT (room_id, closed_date)`. 사유 칸은 없어지고 `closure`에 한 번만.

## 3. 손님 예약 흐름 (ROOM-001 → RSV-001 → RSV-002 → ADM-003)

```mermaid
flowchart TD
    A["객실 추천 /rooms<br/>GET /api/rooms/recommend"] --> B{"날짜 · 인원 검색?"}
    B -- "예" --> C["빈방만: 예약 · 휴무 겹침 없음<br/>max_guest ≥ 인원, is_active=Y"]
    B -- "아니오" --> D["전체 추천 목록"]
    C --> E["정렬: 추천순(조회수 비율x40 + 최근30일 승인 예약 비율x60) · 인기순 · 낮은 가격순<br/>1~3위 '★ 추천', HOT · NEW 뱃지"]
    D --> E
    E --> F["카드 클릭 → POST /api/rooms/{id}/view<br/>(같은 회원 · 방 · 날 1번만 +1, 비회원은 방마다 하루 합쳐 1번)"]
    F --> G{"로그인했나?"}
    G -- "아니오" --> L["로그인 /login"] --> H
    G -- "예" --> H["예약 화면 /reservation/new<br/>날짜 · 인원 · 요청 사항"]
    H --> I["POST /api/reservations"]
    I --> J{"서버 검사<br/>승인 대기 3건 미만 · 객실 사용 중 · 인원<br/>30박 이하 · 365일 안 · 휴무일 · 다른 예약과 겹침"}
    J -- "통과" --> K["저장 status = PENDING<br/>price_per_night = 요금, total_price = 요금 x 숙박일수"]
    J -- "실패" --> X["409 / 400 메시지"] --> H
    K -- "동시 저장 겹침 → DB 제약 23P01" --> X
    K --> N["예약 완료 /reservation/{id}/complete<br/>'승인 대기'"]
    N --> O["관리자 예약 관리 /admin/reservations"]
    O --> P{"승인 / 취소"}
    P -- "승인" --> Q["APPROVED"]
    P -- "취소" --> R["CANCELED (canceled_at · canceled_by 기록)<br/>→ 그 날짜 다시 예약 가능"]
```

## 4. 예약 상태

```mermaid
stateDiagram-v2
    [*] --> PENDING: 손님 예약 (POST /api/reservations)
    PENDING --> APPROVED: 관리자 승인
    PENDING --> CANCELED: 관리자 취소
    APPROVED --> CANCELED: 관리자 취소 (체크인 전까지만)
    CANCELED --> [*]
    note right of PENDING
        PENDING · APPROVED 는 객실을 잡고 있음
        (빈방 판정 · 휴무 지정 · 탈퇴 검사 · DB 겹침 제약에 사용)
        손님은 직접 취소하지 못함 (팀 결정)
    end note
```

## 5. 휴무일 지정 (ADM-002)

```mermaid
flowchart TD
    A["달력에서 날짜 클릭<br/>GET /api/admin/closed-dates/reservation-counts"] --> B["③ 사유 분류 + 상세 → 휴무일로 지정<br/>POST /api/admin/closed-dates (기간은 .../range)"]
    B --> LK["대상 객실 행 잠금<br/>(객실 휴무 = 그 방, 호텔 전체 = 모든 방)<br/>예약 저장과 동시에 와도 한쪽씩 처리"]
    LK --> D{"이미 휴무?<br/>(그날 호텔 전체 휴무 또는 같은 방 휴무)"}
    D -- "예" --> E2["409 ALREADY_CLOSED"]
    D -- "아니오" --> F{"그날 밤 묵는 예약 있음?<br/>(체크인 ≤ 그날 < 체크아웃, 대기 · 승인)<br/>전체 휴무 = 모든 방 / 방 휴무 = 그 방"}
    F -- "N건" --> E3["409 '이 날짜에 예약 N건이 있습니다.<br/>먼저 예약을 취소해 주세요.'"]
    F -- "0건" --> G["저장: 휴무 묶음(closure) 1개 + 날짜 행<br/>→ ④ 휴무 묶음 목록 (예정 · 진행 중 · 종료)"]
    G --> H["손님 예약 · 추천에서 그 날짜 막힘"]
```

- 지난 날짜도 지정 · 해제할 수 있습니다(잘못 넣은 기록을 고치기 위해, 팀 결정 #32).
- 사유 분류는 공사 `CONSTRUCTION` · 점검 `MAINTENANCE` · 행사 `EVENT` · 휴관 `CLOSURE` · 기타 `ETC`. 분류가 없으면 기타로 보고 상세가 필수입니다.
- 기간 지정(`POST .../range`, 최대 31일)은 막힌 날짜를 모두 모아 `409`와 `detail.blockedDates`로 알려 주고, 하나라도 막히면 저장하지 않습니다.
- 기간 해제(`DELETE .../range?startDate=&endDate=&roomId=`, 최대 31일)는 같은 범위(호텔 전체 또는 그 방)에 직접 지정된 휴무만 지웁니다. 날짜가 하나도 안 남은 묶음은 함께 지워집니다.
- 묶음 목록 `GET /api/admin/closures?month=&roomId=`, 묶음 해제 `DELETE /api/admin/closures/{id}`(날짜 행도 함께 삭제). 상태는 오늘(KST) 기준 시작 전 = 예정, 끝난 뒤 = 종료, 그 사이 = 진행 중.
- 전체 객실 달력의 "남은 N실"은 `GET .../available-rooms?month=`(사용 중 객실 − 휴무 객실 − 숙박 중 객실)를 씁니다. `month` 연도는 2000~2100.

## 6. 로그인과 권한 확인

```mermaid
sequenceDiagram
    participant B as 브라우저
    participant N as Next.js (/api 프록시)
    participant F as FastAPI
    participant D as Supabase DB
    B->>N: POST /api/members/login {loginId, password} (+ hotel_device 쿠키)
    N->>F: 그대로 전달
    F->>D: login_attempt 최근 10분 실패 수 확인 (5번이면 429)
    F->>D: member 조회, scrypt 비밀번호 확인 (틀리면 login_attempt 기록)
    F-->>B: Set-Cookie hotel_session (회원번호 + 비밀번호 표식, 서명, 8시간) + 처음 기기면 hotel_device
    B->>N: GET /api/admin/... (쿠키 자동 포함)
    N->>F: 그대로 전달
    F->>D: 쿠키의 회원 조회 · 비밀번호 표식 비교 · role 확인
    alt 로그인 안 됨 / 비밀번호 바뀜
        F-->>B: 401 UNAUTHORIZED
    else ADMIN 아님
        F-->>B: 403 FORBIDDEN
    else 관리자
        F-->>B: 200 결과
    end
```

- 실패 횟수는 처음 보는 기기면 아이디 하나로, 로그인에 성공한 적 있는 기기(`hotel_device`)면 그 기기만 따로 셉니다. 남이 일부러 잠가도 주인은 쓰던 기기로 들어올 수 있습니다.
- 비밀번호 찾기(`POST /api/members/password-reset`)는 시연 전까지 꺼 두어 항상 403입니다.

## 7. 화면 · API 현황 (11-25, dev `251bf9c`)

| 파트 | 화면 (Next.js) | API (`/api` 생략) | 상태 |
|---|---|---|---|
| 1 회원 · 객실 추천 | `/login` `/signup` `/mypage` `/password-reset` `/rooms` `/rooms/{id}` | `members/signup · login · logout · me`, `PUT members/me`, `PUT members/me/password`, `POST members/me/withdraw`, `POST members/password-reset`(403), `GET members/check-id`, `GET rooms/recommend`, `GET rooms/{id}`, `POST rooms/{id}/view` | 구현 (조회수 하루 1번 · 로그인 잠금 DB 저장 · 비밀번호 찾기 꺼 둠 · 회원 화면 디자인) |
| 2 객실 관리 (ADM-001) | `/admin/rooms` | `GET POST admin/rooms`, `GET admin/rooms/summary`, `PUT admin/rooms/{id}`, `PATCH admin/rooms/{id}/status`, `GET room-grades`, `POST GET files`, `DELETE files/{id}` | 구현 (등급 · 전망 · 침대, 사진 Storage 저장, 입력 상한, 예약 있는 방 비활성화 409) |
| 3 예약 일자 관리 (ADM-002) | `/admin/closed-dates` | `GET admin/closed-dates`, `GET .../reservation-counts`, `GET .../available-rooms`, `POST` · `POST range`, `DELETE admin/closed-dates/{id}` · `DELETE range`, `GET admin/closures`, `DELETE admin/closures/{id}` | 구현 (휴무 묶음 · 사유 분류 · 상태 표시, 객실 행 잠금) |
| 4 객실 예약 · 완료 (RSV-001/002) | `/reservation/new` `/reservation/{id}/complete` `/reservation/list` | `POST reservations`, `GET reservations/{id}`, `GET reservations/me`, `GET rooms/{id}/available-dates`, `GET rooms/{id}/quote` | 구현 (1박 요금 기록 · 30박/365일 · 대기 3건 상한 · DB 이중 예약 제약 409) |
| 5 공통 · 예약 관리 (ADM-003) | `/admin/reservations`, 상단 메뉴 | `GET admin/reservations`, `GET admin/reservations/counts`, `PATCH admin/reservations/{id}/approve · cancel`, `GET menus` | 구현 · 테스트 (취소 기록 canceled_at · canceled_by, 손님 메뉴: 객실 추천 · 내 예약 · 마이페이지) |

전체 API 목록과 입력 · 출력 모양은 서버를 켜고 http://localhost:8000/docs 에서 봅니다.
