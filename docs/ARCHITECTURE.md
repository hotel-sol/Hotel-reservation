# 태양의 호텔 — 시스템 구조 한눈에 보기

GitHub에서 그림(Mermaid)으로 보입니다. 기준: **dev 브랜치, 11-24**(Step 1 + Step 2 진행분). DB는 Supabase(PostgreSQL) 팀 프로젝트 하나: 각자 개발은 스키마 hotel_<이름>, 시연은 공용 스키마 hotel. DB 시간대는 `Asia/Seoul`(11-24부터).

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
        S["services<br/>추천 점수 · 빈방 판정"]
        M["models<br/>(SQLAlchemy)"]
    end
    DB[("Supabase PostgreSQL<br/>스키마 hotel")]

    U -- "화면 요청" --> P
    U -- "API 호출 /api/* + 로그인 쿠키" --> RW
    RW --> R
    R --> S --> M
    R --> M
    M --> DB
```

- 브라우저는 `localhost:3000` 한 주소만 봅니다. 그래서 로그인 쿠키(HttpOnly, SameSite=Lax)가 그대로 동작하고 CORS 설정이 필요 없습니다.
- DDL: `docs/hotel_reservation_ddl.sql`. 개발 DB 만들기: `backend`에서 `uv run python -m app.db.init_db`(내 스키마 `hotel_<이름>`에만. 공용 `hotel`은 `--reset-shared`가 있어야 지워짐).

## 2. DB 구조 (ERD)

```mermaid
erDiagram
    MEMBER ||--o{ RESERVATION : "예약한다"
    ROOM ||--o{ RESERVATION : "예약된다"
    ROOM |o--o{ CLOSED_DATE : "쉬는 날 (room_id NULL = 호텔 전체)"
    ROOM ||--o{ ATTACH_FILE : "사진 (target_type='ROOM')"
    MENU |o--o{ MENU : "상위 메뉴"

    MEMBER {
        bigint member_id PK
        varchar login_id UK "로그인 아이디"
        varchar password "scrypt$salt$hash"
        varchar name
        varchar phone
        varchar email UK
        varchar role "USER / ADMIN"
        datetime created_at
    }
    ROOM {
        bigint room_id PK
        varchar room_name UK
        varchar room_type
        int max_guest "1 이상"
        int price "1박 요금, 0 초과"
        varchar description
        int view_count "추천 점수에 사용"
        char is_active "Y / N (삭제 대신 비활성화)"
        datetime created_at
    }
    RESERVATION {
        bigint reservation_id PK
        bigint member_id FK
        bigint room_id FK
        date check_in_date
        date check_out_date "체크인보다 뒤"
        int guest_count
        int total_price "1박 요금 x 숙박일수"
        varchar status "PENDING / APPROVED / CANCELED"
        varchar request_memo "최대 200자"
        datetime created_at
        datetime updated_at "상태 바뀐 시각"
    }
    CLOSED_DATE {
        bigint closed_date_id PK
        bigint room_id FK "NULL = 호텔 전체 휴무"
        date closed_date
        varchar reason
        datetime created_at
    }
    ATTACH_FILE {
        bigint file_id PK
        varchar target_type "예: ROOM"
        bigint target_id "그 대상의 번호"
        varchar original_name
        varchar saved_path
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

## 3. 손님 예약 흐름 (ROOM-001 → RSV-001 → RSV-002 → ADM-003)

```mermaid
flowchart TD
    A["객실 추천 /rooms<br/>GET /api/rooms/recommend"] --> B{"날짜 · 인원 검색?"}
    B -- "예" --> C["빈방만: 예약 · 휴무 겹침 없음<br/>max_guest ≥ 인원, is_active=Y"]
    B -- "아니오" --> D["전체 추천 목록"]
    C --> E["정렬: 추천순(조회수x0.3 + 최근30일 예약x0.7) · 인기순 · 낮은 가격순<br/>추천순 1등에 '추천'"]
    D --> E
    E --> F["카드 클릭 → POST /api/rooms/{id}/view (조회수 +1)"]
    F --> G{"로그인했나?"}
    G -- "아니오" --> L["로그인 /login"] --> H
    G -- "예" --> H["예약 화면 /reservation/new<br/>날짜 · 인원 · 요청 사항"]
    H --> I["POST /api/reservations"]
    I --> J{"서버 검사<br/>객실 사용 중 · 인원 · 휴무일 · 다른 예약과 겹침"}
    J -- "통과" --> K["저장 status = PENDING<br/>total_price = 요금 x 숙박일수"]
    J -- "실패" --> X["409 / 400 메시지"] --> H
    K --> N["예약 완료 /reservation/{id}/complete<br/>'승인 대기'"]
    N --> O["관리자 예약 관리 /admin/reservations"]
    O --> P{"승인 / 취소"}
    P -- "승인" --> Q["APPROVED"]
    P -- "취소" --> R["CANCELED → 그 날짜 다시 예약 가능"]
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
        (빈방 판정 · 휴무 지정 · 탈퇴 검사에 사용)
    end note
```

## 5. 휴무일 지정 (ADM-002)

```mermaid
flowchart TD
    A["달력에서 날짜 클릭<br/>GET /api/admin/closed-dates/reservation-counts"] --> B["③ 사유 입력 → 휴무일로 지정<br/>POST /api/admin/closed-dates"]
    B --> D{"이미 휴무?<br/>(그날 호텔 전체 휴무 또는 같은 방 휴무)"}
    D -- "예" --> E2["409 ALREADY_CLOSED"]
    D -- "아니오" --> F{"그날 밤 묵는 예약 있음?<br/>(체크인 ≤ 그날 < 체크아웃, 대기 · 승인)<br/>전체 휴무 = 모든 방 / 방 휴무 = 그 방"}
    F -- "N건" --> E3["409 '이 날짜에 예약 N건이 있습니다.<br/>먼저 예약을 취소해 주세요.'"]
    F -- "0건" --> G["저장 → ④ 이번 달 휴무일 목록"]
    G --> H["손님 예약 · 추천에서 그 날짜 막힘"]
```

- 지난 날짜도 지정 · 해제할 수 있습니다(잘못 넣은 기록을 고치기 위해, 팀 결정 #32).
- 기간 지정(`POST .../range`, 최대 31일)은 막힌 날짜를 모두 모아 `409`와 `detail.blockedDates`로 알려 주고, 하나라도 막히면 저장하지 않습니다.
- 기간 해제(`DELETE .../range?startDate=&endDate=&roomId=`)는 같은 범위(호텔 전체 또는 그 방)에 직접 지정된 휴무만 지웁니다.
- 전체 객실 달력의 "남은 N실"은 `GET .../available-rooms?month=`(사용 중 객실 − 휴무 객실 − 숙박 중 객실)를 씁니다.

## 6. 로그인과 권한 확인

```mermaid
sequenceDiagram
    participant B as 브라우저
    participant N as Next.js (/api 프록시)
    participant F as FastAPI
    participant D as Supabase DB
    B->>N: POST /api/members/login {loginId, password}
    N->>F: 그대로 전달
    F->>D: member 조회, scrypt 비밀번호 확인 (5번 틀리면 10분 잠금)
    F-->>B: Set-Cookie hotel_session (회원번호 + 비밀번호 표식, 서명, 8시간)
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

## 7. 화면 · API 현황 (11-24, dev)

| 파트 | 화면 (Next.js) | API (`/api` 생략) | 상태 |
|---|---|---|---|
| 1 회원 · 객실 추천 | `/login` `/signup` `/mypage` `/password-reset` `/rooms` | `members/signup · login · logout · me`, `PUT members/me`, `PUT members/me/password`, `POST members/me/withdraw`, `POST members/password-reset`, `GET rooms/recommend`, `POST rooms/{id}/view` | 구현 (마이페이지 정보 수정 · 비밀번호 변경 · 탈퇴, 비밀번호 찾기 화면 포함) |
| 2 객실 관리 (ADM-001) | `/admin/rooms` | `GET POST admin/rooms`, `GET admin/rooms/summary`, `PUT admin/rooms/{id}`, `PATCH admin/rooms/{id}/status`, `POST GET files`, `DELETE files/{id}` | 구현 (사진 업로드 · 요약 카드 · 미래 예약 객실 수정 제한 · 시연용 40실 `demo_seed.sql`) |
| 3 예약 일자 관리 (ADM-002) | `/admin/closed-dates` | `GET admin/closed-dates`, `GET admin/closed-dates/reservation-counts`, `GET admin/closed-dates/available-rooms`, `POST` · `POST range`, `DELETE admin/closed-dates/{id}` · `DELETE range` | 구현 (객실 선택 · 달력 · 기간 지정/해제 · Shift+클릭 · 이번 달 목록) |
| 4 객실 예약 · 완료 (RSV-001/002) | `/reservation/new` `/reservation/{id}/complete` `/reservation/list` | `POST reservations`, `GET reservations/{id}`, `GET reservations/me`, `GET rooms/{id}` | 구현. **남음:** 지난 날짜 차단, `rooms/{id}/available-dates`(501, 이슈 #27) |
| 5 공통 · 예약 관리 (ADM-003) | `/admin/reservations`, 상단 메뉴 | `GET admin/reservations`, `PATCH admin/reservations/{id}/approve · cancel`, `GET menus` | 구현 |

전체 API 목록과 입력 · 출력 모양은 서버를 켜고 http://localhost:8000/docs 에서 봅니다.
