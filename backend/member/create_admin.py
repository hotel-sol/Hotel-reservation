"""관리자 계정 만들기: python create_admin.py <아이디> <이름>

- 아이디가 없으면 새 관리자 계정을 만들고, 있으면 그 계정을 관리자로 바꾼다.
- 비밀번호는 화면에 보이지 않게 두 번 입력받는다(명령어 기록에 남지 않게 인자로 받지 않는다).
- 가입 화면으로는 관리자가 될 수 없어서 서버에 접속할 수 있는 사람만 이걸로 만든다.
"""
import getpass
import sys

import pymysql

from member import LOGIN_ID_RE, connect, hash_password


def ask_password() -> str:
    while True:
        first = getpass.getpass("비밀번호(8자 이상): ")
        if len(first) < 8:
            print("8자 이상이어야 합니다.")
            continue
        if first != getpass.getpass("비밀번호 확인: "):
            print("두 번 입력한 비밀번호가 다릅니다.")
            continue
        return first


def create_admin(login_id: str, name: str, password: str) -> str:
    """새로 만들면 'created', 기존 계정을 바꾸면 'promoted'."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT member_id FROM member WHERE login_id = %s", (login_id,))
            if cur.fetchone():
                cur.execute("UPDATE member SET role = 'ADMIN', password = %s WHERE login_id = %s",
                            (hash_password(password), login_id))
                result = "promoted"
            else:
                cur.execute("INSERT INTO member (login_id, password, name, role) VALUES (%s, %s, %s, 'ADMIN')",
                            (login_id, hash_password(password), name))
                result = "created"
        conn.commit()
        return result
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("사용법: python create_admin.py <아이디> <이름>")
    login_id, name = sys.argv[1], sys.argv[2].strip()
    if not LOGIN_ID_RE.match(login_id) or not name:
        sys.exit("아이디는 영문 · 숫자 · _ 4~50자, 이름은 비울 수 없습니다.")
    try:
        result = create_admin(login_id, name, ask_password())
    except pymysql.MySQLError as e:
        sys.exit(f"DB 오류: {e}")
    print(f"'{login_id}' 관리자 {'계정을 만들었습니다' if result == 'created' else '권한을 주고 비밀번호를 바꿨습니다'}.")
