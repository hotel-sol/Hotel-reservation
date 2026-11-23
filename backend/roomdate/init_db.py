"""개발용 DB를 지우고 다시 만든다: python init_db.py [--no-seed]

DB_NAME(기본 hotel)을 DROP 후 팀 DDL(docs/hotel_reservation_ddl.sql), dev_seed.sql 순서로 실행한다.
공용 DB에는 쓰지 말 것(DROP DATABASE를 한다).
"""
import os
import sys
from pathlib import Path

import pymysql

from roomdate import connect

HERE = Path(__file__).parent
TEAM_DDL = HERE.parent.parent / "docs" / "hotel_reservation_ddl.sql"


def run_sql_file(cursor, path: Path) -> None:
    # ponytail: ';' 기준 단순 분리. 프로시저 · 트리거를 넣으면 mysql 클라이언트로 바꾼다.
    for statement in path.read_text(encoding="utf-8").split(";"):
        code = [l for l in statement.splitlines() if not l.strip().startswith("--")]
        if "\n".join(code).strip():
            cursor.execute(statement)


def init_db(db_name: str, seed: bool = True) -> None:
    conn = connect(database="")
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            cur.execute(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cur.execute(f"USE `{db_name}`")
            run_sql_file(cur, TEAM_DDL)
            if seed:
                run_sql_file(cur, HERE / "dev_seed.sql")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    name = os.getenv("DB_NAME", "hotel")
    seed = "--no-seed" not in sys.argv
    try:
        init_db(name, seed=seed)
        print(f"'{name}' 생성 완료")
        # 공용 개발용 관리자: 비밀번호는 저장소에 두지 않고 환경변수로 받는다(팀에 따로 전달).
        admin_password = os.getenv("ADMIN_PASSWORD")
        if seed and admin_password:
            from create_admin import DEV_ADMIN_ID, DEV_ADMIN_NAME, create_admin
            create_admin(DEV_ADMIN_ID, DEV_ADMIN_NAME, admin_password)
            print(f"관리자 계정 '{DEV_ADMIN_ID}' 생성 완료")
        elif seed:
            print("관리자 계정 없음: ADMIN_PASSWORD 환경변수를 넣고 다시 실행하면 admin01이 생깁니다.")
    except (pymysql.MySQLError, ValueError) as e:
        sys.exit(f"DB 초기화 실패: {e}")
