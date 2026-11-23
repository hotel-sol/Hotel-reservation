# layout — 공통 상단 메뉴(페이지 분할)

화면설계서의 "HOTEL" 머리줄입니다. 화면마다 따로 만들지 않고 이 파일 하나를 붙입니다. 외부 라이브러리는 없습니다.

**로그인한 사람의 `member.role`로 메뉴가 갈립니다.**

| 로그인 상태 | 메뉴 |
|---|---|
| `ADMIN` (관리자) | HOTEL 관리자 · 객실 관리 · 예약 일자 관리 · 예약 관리 · OOO님 · 로그아웃 |
| `USER` (회원) | HOTEL · 객실 추천 · 내 예약 · OOO님 · 로그아웃 |
| 로그인 안 함 | HOTEL · 객실 추천 · 로그인 · 회원가입 |

## 붙이는 법
각 화면 HTML의 `<body>` 맨 위에:
```html
<header data-hotel-header></header>          <!-- 관리자 전용 화면은 data-hotel-header="admin" -->
<script src="/layout/layout.js"></script>
```
- 지금 주소와 같은 메뉴가 굵게(현재 화면) 표시됩니다.
- `"admin"` 화면에 관리자가 아닌 사람이 들어오면 `/login?next=<원래 주소>`로 보냅니다. 화면에서 돌려보내는 것일 뿐이고, 진짜 막는 건 각 API의 401/403입니다.

메인 앱에서 이 폴더를 열어 주는 한 줄:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/layout", StaticFiles(directory="frontend/layout"), name="layout")
```

## 회원 기능과의 연결 (자체 회원가입, `backend/member`)
머리줄은 페이지를 열 때 **`GET /api/members/me`** 를 한 번 부릅니다.
- 로그인 상태: `200 {"memberId": 1, "loginId": "admin", "name": "관리자", "role": "ADMIN"}` (`role`은 `member.role` 그대로)
- 로그인 안 함: `401`
- 로그인 정보는 세션 쿠키로 갑니다(같은 주소라 `fetch`가 자동으로 보냄).
- 링크: 로그인 `/login`, 회원가입 `/signup`, 내 정보 `/mypage`("OOO님"), 로그아웃 `/logout` (모두 `backend/member`가 제공)

## 미리보기
```
cd frontend/layout
python -m http.server 8020      # http://127.0.0.1:8020/preview.html
```
위쪽 버튼으로 관리자 / 회원 / 로그인 안 함을 바꿔 볼 수 있습니다(미리보기만 `/api/members/me` 응답을 흉내 냄).

## 팀 확인 필요
- **화면 주소 규칙**: API 주소 뒤에 `/page`(`/admin/closed-dates/page`는 이미 이렇게 동작). 객실 관리 `/admin/rooms/page`, 예약 관리 `/admin/reservations/page`, 객실 추천 `/rooms/page`, 내 예약 `/reservations/page`. 바꾸려면 `layout.js`의 `MENUS`만 고칩니다.
- **메뉴는 코드에 고정**: MENU 테이블(공통, `role` 칸)과 같은 내용입니다. 메뉴 API가 생기면 거기서 받아 오도록 바꿉니다.
