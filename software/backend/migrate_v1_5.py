"""moodnote DB 를 v1.4 에서 v1.5 로 올린다. (의견 보내기용 'feedback' 테이블 추가. 기존 데이터는 지워지지 않는다)
실행:  python3 migrate_v1_5.py      (root 비밀번호를 물어본다. 두 번 실행해도 안전하다)
필요한 것: pip install pymysql
새로 만든 서버(setup_server.sh)는 schema_mysql.sql 로 이미 이 테이블이 있어서 이 파일이 필요 없다."""
import getpass
import os
import pathlib
import sys

import pymysql


def main():
    pw = os.environ.get("DB_ADMIN_PASSWORD") or getpass.getpass("root password: ")
    try:
        conn = pymysql.connect(host="127.0.0.1", user="root", password=pw, database="moodnote")
    except pymysql.err.OperationalError as e:
        sys.exit(f"[ABORTED] Could not connect to the DB: {e}")

    # migrate_v1_5.sql 에서 USE 줄과 주석을 빼고 CREATE TABLE 문 하나를 그대로 실행한다. (SQL 이 한 곳에만 있게)
    sql_path = pathlib.Path(__file__).with_name("migrate_v1_5.sql")
    lines = [l for l in sql_path.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.lstrip().startswith("--") and not l.upper().startswith("USE ")]
    with conn.cursor() as cur:
        cur.execute("\n".join(lines))
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='feedback'")
        ok = cur.fetchone()[0] == 1
    conn.commit()
    conn.close()
    print("- feedback table: ready" if ok else "- feedback table: could not be created")
    print("Done")


if __name__ == "__main__":
    main()
