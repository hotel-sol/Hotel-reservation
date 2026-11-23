# member — 자체 회원가입 · 로그인 · 내 정보

담당 테이블 `member`. 외부 로그인(구글 등) 없이 아이디 · 비밀번호로 가입합니다. 새 패키지 없이 표준 라이브러리만 씁니다.

## API (실제 주소는 앞에 `/api`, 예: `/api/members/login`)
| 메서드 · 경로 | 설명 | 주요 오류 |
|---|---|---|
| `POST /members/signup` `{loginId, password, name, phone?, email?}` | 회원가입. **항상 `USER`** | 400 형식, 409 아이디 · 이메일 중복, 422 비밀번호 8자 미만 |
| `POST /members/login` `{loginId, password}` | 로그인, 세션 쿠키 발급(8시간) | 401, **429 5번 틀리면 10분 잠금** |
| `POST /members/logout`, `GET /logout` | 로그아웃 | — |
| `GET /members/me` | 지금 로그인한 사람 `{memberId, loginId, name, phone, email, role}` | 401 |
| `PUT /members/me` `{name, phone?, email?}` | 내 정보 수정 | 400, 409 이메일 중복 |
| `PUT /members/me/password` `{currentPassword, newPassword}` | 비밀번호 변경. **다른 기기 로그인은 끊김** | 400 현재 비밀번호 틀림 |
| `POST /members/me/withdraw` `{password}` | 탈퇴 | 400 비밀번호 틀림 · 관리자, 409 진행 중 예약 |
| `POST /members/password-reset` `{loginId, email, newPassword}` | 비밀번호 찾기 | 400 아이디 · 이메일 불일치, 429 |

화면: `/signup`, `/login`, `/mypage`(정보 수정 · 비밀번호 변경 · 탈퇴), `/password-reset`.
로그인 화면은 `?next=/원래주소`를 받으면 로그인 뒤 그리로 돌아갑니다(같은 사이트 주소만). 없으면 관리자는 `/admin/rooms/page`, 회원은 `/rooms/page`.

## 관리자 계정 만들기
가입 화면으로는 관리자가 될 수 없습니다(`role`을 보내도 무시). 서버에 접속할 수 있는 사람이 만듭니다.
```
python -m member.create_admin <아이디> <이름>   # backend 폴더에서. 비밀번호는 화면에 안 보이게 두 번 입력
```
아이디가 없으면 관리자 계정을 새로 만들고, 있으면 그 계정을 관리자로 바꾸고 비밀번호를 새로 정합니다. 환경변수 `ADMIN_PASSWORD`가 있으면 입력 없이 그 값을 씁니다.

### 팀 공용 개발용 관리자 `admin01`
- 개발 DB를 만들 때 `ADMIN_PASSWORD`를 넣으면 자동으로 생깁니다: `backend/.env`에 `ADMIN_PASSWORD=<팀 공용 비밀번호>`를 넣고 `python -m db.init_db`
- **비밀번호는 저장소에 두지 않습니다**(공개 저장소). 팀 채팅으로 받으세요.
- 개발 DB 전용입니다. 실제 서비스 DB에는 다른 비밀번호로 따로 만드세요.

## 비밀번호: salt + 해시
- 회원마다 무작위 salt 16바이트 + `hashlib.scrypt` → `password` 칸에 `scrypt$<salt>$<hash>`로 저장(168자).
- 원래 비밀번호는 저장하지 않습니다. 같은 비밀번호도 salt가 달라 저장값이 다릅니다. 비교는 `hmac.compare_digest`.

## 로그인 유지(세션)
- 쿠키 = `회원번호.만료시각.비밀번호표식.서명`(HMAC). 손으로 고치면 무효. `HttpOnly`, `SameSite=Lax`.
- 비밀번호표식 덕분에 **비밀번호를 바꾸거나 탈퇴하면 예전 쿠키가 모두 무효**가 됩니다.
- **함께 쓰는 서버에서는 환경변수 `SESSION_SECRET`을 꼭 설정**하세요. 없으면 서버 로그에 경고가 뜨고, 서버를 다시 켤 때 모두 로그아웃됩니다.
- role은 요청마다 DB에서 읽어서 관리자로 바꾸면 바로 반영됩니다.

## 탈퇴
`reservation.member_id`가 회원을 참조해서(FK) 행을 지우면 예약 기록이 깨집니다. 그래서 **행은 남기고 개인정보만 지웁니다**: `login_id = withdrawn_<번호>`, `name = 탈퇴회원`, 전화번호 · 이메일 NULL, 비밀번호 `!`(어떤 비밀번호로도 로그인 불가). 같은 아이디로 다시 가입할 수 있습니다.
- 진행 중인 예약(대기 · 승인, 체크아웃 전)이 있으면 탈퇴할 수 없습니다.
- 관리자 계정은 탈퇴할 수 없습니다.

## 다른 파트에서 쓰는 법
```python
from member.member import current_member, require_admin

@router.get("/reservations/mine")
def mine(member: dict = Depends(current_member)): ...      # 로그인한 사람만, member["member_id"]

@router.get("/admin/rooms")
def rooms(admin: dict = Depends(require_admin)): ...        # 관리자만(401 / 403)
```

## 실행
실행 · 테스트 · 접속값은 [backend/readme.md](../readme.md)를 따릅니다(`uvicorn main:app`, `python -m pytest`).

## 한계 (공개 배포 전에 바꿀 것)
- **비밀번호 찾기**: 메일 서버가 없어서 "아이디 + 가입 이메일"이 맞으면 바로 바꿉니다. 이메일을 아는 남도 바꿀 수 있으니, 배포 전에는 메일로 보내는 일회용 링크로 바꿔야 합니다. 이메일 없이 가입한 회원은 스스로 찾을 수 없어서, 관리자가 DB에서 이메일을 넣어 준 뒤 찾게 해야 합니다.
- **로그인 잠금**: 서버 메모리에 기록해서, 서버를 다시 켜거나 여러 대로 늘리면 초기화됩니다.
