# member — 자체 회원가입 · 로그인 · 로그아웃

담당 테이블 `member`. 외부 로그인(구글 등) 없이 아이디 · 비밀번호로 가입합니다. 새 패키지 없이 표준 라이브러리만 씁니다.

## API
| 메서드 · 경로 | 설명 | 오류 |
|---|---|---|
| `POST /members/signup` `{"loginId", "password", "name", "phone"?, "email"?}` | 회원가입. **항상 `USER`로 가입** | 400 형식 오류, 409 `DUPLICATE_LOGIN_ID` · `DUPLICATE_EMAIL`, 422 비밀번호 8자 미만 |
| `POST /members/login` `{"loginId", "password"}` | 로그인. 세션 쿠키 `hotel_session` 발급(8시간) | 401 "아이디 또는 비밀번호가 맞지 않습니다." |
| `POST /members/logout` | 로그아웃(쿠키 삭제) | — |
| `GET /members/me` | 지금 로그인한 사람 `{"memberId", "loginId", "name", "role"}` | 401 |
| `GET /signup`, `GET /login` | 가입 · 로그인 화면 | — |
| `GET /logout` | 로그아웃 후 `/login`으로 이동(상단 메뉴 링크용) | — |

- 로그인 화면은 `?next=/원래주소`를 받으면 로그인 뒤 그리로 돌아갑니다(같은 사이트 주소만). 없으면 관리자는 `/admin/rooms/page`, 회원은 `/rooms/page`.
- 가입 직후에는 `/login?joined=1`로 가서 로그인합니다.

## 비밀번호: 소금(salt) + 해시
- 회원마다 무작위 소금 16바이트를 만들고 `hashlib.scrypt`로 해시합니다.
- `password` 칸에 `scrypt$<소금 hex>$<해시 hex>` 한 줄로 저장합니다(DDL의 VARCHAR(255) 안에 들어감). 원래 비밀번호는 어디에도 저장하지 않습니다.
- 같은 비밀번호라도 소금이 달라서 저장값이 다릅니다. 비교는 `hmac.compare_digest`로 합니다.

## 로그인 유지(세션)
- 쿠키 값 = `회원번호.만료시각.서명`. 서명은 서버 비밀키(`SESSION_SECRET` 환경변수)로 만든 HMAC이라 손으로 고치면 무효가 됩니다. `HttpOnly`, `SameSite=Lax`.
- `SESSION_SECRET`이 없으면 서버를 켤 때마다 새로 만들어서, 서버를 다시 켜면 모두 로그아웃됩니다. 함께 쓰는 서버에서는 꼭 설정하세요.
- 역할(`role`)은 요청마다 DB에서 읽어서, 관리자로 바꾸면 바로 반영됩니다.

## 다른 파트에서 쓰는 법
```python
from member import current_member, require_admin

@router.get("/reservations/mine")
def mine(member: dict = Depends(current_member)): ...      # 로그인한 사람만, member["member_id"]

@router.get("/admin/rooms")
def rooms(admin: dict = Depends(require_admin)): ...        # 관리자만(401 / 403)
```

## 관리자 계정 만들기
가입으로는 관리자가 될 수 없습니다(`role`을 보내도 무시). 가입한 뒤 DB에서 바꿉니다.
```sql
UPDATE member SET role = 'ADMIN' WHERE login_id = '관리자아이디';
```

## 실행
```
pip install -r requirements.txt
uvicorn member:app --reload      # http://127.0.0.1:8000/signup
DB_PORT=3307 python -m pytest -q # hotel_test_member DB를 팀 DDL(docs/hotel_reservation_ddl.sql)로 새로 만들어 테스트
```
접속값은 환경변수 `DB_HOST`, `DB_PORT`(기본 3306), `DB_USER`, `DB_PASSWORD`, `DB_NAME`(기본 hotel), `SESSION_SECRET`.

## 아직 안 한 것
- 로그인 시도 횟수 제한(공개 배포 전에 추가)
- 회원 정보 수정 · 탈퇴 · 비밀번호 찾기(설계서에 없음)
- DB 연결은 임시로 이 파일 안에 있음. 공통 `db/connect.py`가 채워지면 그쪽으로 바꿈.
