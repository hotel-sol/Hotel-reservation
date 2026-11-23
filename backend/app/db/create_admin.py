"""관리자 계정 만들기. backend 폴더에서: uv run python -m app.db.create_admin <아이디> <이름>

- 아이디가 없으면 새 관리자 계정을 만들고, 있으면 그 계정을 관리자로 바꾸고 비밀번호를 새로 정한다.
- 비밀번호는 화면에 보이지 않게 두 번 입력받는다(명령어 기록에 남지 않게 인자로는 받지 않는다).
- 가입 화면으로는 관리자가 될 수 없어서 서버에 접속할 수 있는 사람만 이걸로 만든다.
- 팀 공용 개발용 관리자 admin01은 init_db가 .env의 ADMIN_PASSWORD로 자동으로 만든다.
"""
import getpass
import re
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Member

DEV_ADMIN_ID = "admin01"
DEV_ADMIN_NAME = "관리자"
MIN_PASSWORD = 8
LOGIN_ID_RE = re.compile(r"^[A-Za-z0-9_]{4,50}$")


def create_admin(login_id: str, name: str, password: str) -> str:
    """새로 만들면 'created', 기존 계정을 바꾸면 'promoted'."""
    if len(password) < MIN_PASSWORD:
        raise ValueError(f"관리자 비밀번호는 {MIN_PASSWORD}자 이상이어야 합니다.")
    with SessionLocal() as db:
        member = db.scalar(select(Member).where(Member.login_id == login_id))
        if member:
            member.role, member.password = "ADMIN", hash_password(password)
            result = "promoted"
        else:
            db.add(Member(login_id=login_id, password=hash_password(password), name=name, role="ADMIN"))
            result = "created"
        db.commit()
    return result


def ask_password() -> str:
    while True:
        first = getpass.getpass(f"비밀번호({MIN_PASSWORD}자 이상): ")
        if len(first) < MIN_PASSWORD:
            print(f"{MIN_PASSWORD}자 이상이어야 합니다.")
        elif first != getpass.getpass("비밀번호 확인: "):
            print("두 번 입력한 비밀번호가 다릅니다.")
        else:
            return first


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("사용법: uv run python -m app.db.create_admin <아이디> <이름>")
    login_id, name = sys.argv[1], sys.argv[2].strip()
    if not LOGIN_ID_RE.match(login_id) or not name:
        sys.exit("아이디는 영문 · 숫자 · _ 4~50자, 이름은 비울 수 없습니다.")
    result = create_admin(login_id, name, ask_password())
    print(f"'{login_id}' 관리자 {'계정을 만들었습니다' if result == 'created' else '권한을 주고 비밀번호를 바꿨습니다'}.")
