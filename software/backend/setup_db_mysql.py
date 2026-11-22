"""MoodNote DB 구축 스크립트 (MySQL / MariaDB)

한 번 실행하면 아래를 순서대로 한다.
  1) schema_mysql.sql 로 DB와 테이블 12개 + 뷰 1개를 만든다.
  2) mood_words.csv 의 무드 단어 100개를 mood_words 테이블에 넣는다. (일기 테이블이 이 테이블을 참조하므로 반드시 먼저)
  3) (선택 --seed) seed_dev_mysql.sql 의 가짜 데이터를 넣는다.
  4) (선택 --app-user 이름) API가 쓸 권한 제한 계정을 만든다. root로 API를 돌리면 안 된다.
  5) 결과를 확인해서 출력한다.

같은 폴더에 있어야 하는 파일: schema_mysql.sql, mood_words.csv, (seed를 쓰면) seed_dev_mysql.sql

사용 예
  python setup_db_mysql.py                          테이블과 단어만 만든다
  python setup_db_mysql.py --seed                   + 개발용 가짜 데이터
  python setup_db_mysql.py --seed --app-user moodnote_app
  python setup_db_mysql.py --reset --seed           moodnote DB를 지우고 처음부터 (주의: 데이터가 사라진다)

필요한 것: pip install pymysql cryptography
"""
import argparse
import csv
import getpass
import os
import re
import sys

import pymysql
from pymysql.constants import CLIENT

HERE = os.path.dirname(os.path.abspath(__file__))
DB_NAME = "moodnote"
EXPECTED_TABLES = 13  # users, user_profile, relationships, mood_words, diary_entries, ai_feedback,
                      # daily_condition, menstrual_cycles, self_model, safety_events, consents, feedback, user_identities


def parse_args():
    p = argparse.ArgumentParser(description="Build the MoodNote DB")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=3306)
    p.add_argument("--user", default="root", help="admin account that can create the DB (default root)")
    p.add_argument("--words", default=os.path.join(HERE, "mood_words.csv"), help="CSV exported from the mood_words_out sheet")
    p.add_argument("--seed", action="store_true", help="also insert fake development data")
    p.add_argument("--app-user", default=None, help="account name for the API (e.g. moodnote_app)")
    p.add_argument("--app-host", default="localhost", help="host that account may connect from (default localhost)")
    p.add_argument("--reset", action="store_true", help="drop the existing moodnote DB and recreate it")
    return p.parse_args()


def fail(msg):
    sys.exit(f"\n[ABORTED] {msg}")


def load_words(path):
    """CSV를 읽어 검사한 뒤 INSERT용 튜플 목록으로 돌려준다."""
    if not os.path.exists(path):
        fail(f"{path} not found. Download the mood_words_out sheet as CSV and save it as mood_words.csv in this folder.")
    with open(path, encoding="utf-8-sig", newline="") as f:  # utf-8-sig: 엑셀이 붙이는 BOM 제거
        rows = list(csv.DictReader(f))
    need = ["id", "word_ko", "word_en", "grid_row", "grid_col", "energy", "pleasantness", "zone"]
    if not rows or any(c not in rows[0] for c in need):
        fail(f"The CSV header must be {need}. Found: {list(rows[0].keys()) if rows else 'empty'}")
    if len(rows) != 100:
        fail(f"Expected 100 word rows, found {len(rows)}.")
    out, problems = [], []
    for r in rows:
        ko = r["word_ko"].strip()          # '겁먹은 ' 처럼 뒤에 붙은 공백 제거
        en = r["word_en"].strip() or None
        if not ko:
            problems.append(f"id {r['id']}: word_ko is empty")
        out.append((int(r["id"]), ko, en, int(r["grid_row"]), int(r["grid_col"]),
                    int(r["energy"]), int(r["pleasantness"]), r["zone"].strip()))
    if problems:
        fail("The word sheet has empty cells:\n  " + "\n  ".join(problems))
    return out


def run_script(cur, path):
    """SQL 파일 전체를 한 번에 실행한다. (MULTI_STATEMENTS 연결 필요)"""
    sql = open(path, encoding="utf-8").read()
    cur.execute(sql)
    while cur.nextset():       # 여러 문장 중 뒤쪽에서 난 오류도 여기서 드러난다
        pass


def check_version(cur):
    cur.execute("SELECT VERSION()")
    ver = cur.fetchone()[0]
    print(f"Server version: {ver}")
    if "mariadb" in ver.lower():
        print("  (This is MariaDB. Fine for development, but not identical to MySQL.)")
        return
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", ver)
    if m and tuple(map(int, m.groups())) < (8, 0, 16):
        fail("MySQL 8.0.16 or newer is required (older versions ignore CHECK constraints).")


def main():
    a = parse_args()
    for fn in ["schema_mysql.sql"] + (["seed_dev_mysql.sql"] if a.seed else []):
        if not os.path.exists(os.path.join(HERE, fn)):
            fail(f"{fn} is not in this folder.")
    words = load_words(a.words)  # DB를 건드리기 전에 CSV부터 검사한다

    pw = os.environ.get("DB_ADMIN_PASSWORD") or getpass.getpass(f"Password for {a.user}: ")
    try:
        conn = pymysql.connect(host=a.host, port=a.port, user=a.user, password=pw,
                               charset="utf8mb4", client_flag=CLIENT.MULTI_STATEMENTS, autocommit=True)
    except pymysql.err.OperationalError as e:
        fail(f"Could not connect to the DB: {e}\n  Check that MySQL is running and the host/port/account/password are correct.")
    cur = conn.cursor()
    check_version(cur)

    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s", (DB_NAME,))
    existing = cur.fetchone()[0]
    if existing:
        if not a.reset:
            fail(f"The '{DB_NAME}' DB already has {existing} tables. To recreate it from scratch add --reset (ALL data will be lost).")
        if input(f"This will delete ALL data in the '{DB_NAME}' DB. To continue type 'delete {DB_NAME}': ").strip() != f"delete {DB_NAME}":
            fail("Input did not match, cancelled. Nothing was deleted.")
        cur.execute(f"DROP DATABASE `{DB_NAME}`")
        print("Existing DB dropped.")

    print("1) Running the schema ...")
    run_script(cur, os.path.join(HERE, "schema_mysql.sql"))

    print("2) Inserting the 100 mood words ...")
    cur.execute(f"USE `{DB_NAME}`")
    cur.executemany(
        "INSERT INTO mood_words (id, word_ko, word_en, grid_row, grid_col, energy, pleasantness, zone) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", words)

    if a.seed:
        print("3) Inserting fake development data ...")
        run_script(cur, os.path.join(HERE, "seed_dev_mysql.sql"))

    if a.app_user:
        app_pw = os.environ.get("DB_APP_PASSWORD") or getpass.getpass(f"New password for the API account '{a.app_user}': ")
        if len(app_pw) < 8:
            fail("The API account password must be at least 8 characters. (The DB and schema were already created.)")
        who = f"`{a.app_user}`@%s"
        cur.execute(f"CREATE USER IF NOT EXISTS {who} IDENTIFIED BY %s", (a.app_host, app_pw))
        cur.execute(f"ALTER USER {who} IDENTIFIED BY %s", (a.app_host, app_pw))
        cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{DB_NAME}`.* TO {who}", (a.app_host,))
        print(f"4) Creating the API account '{a.app_user}'@'{a.app_host}' (SELECT/INSERT/UPDATE/DELETE on this DB only)")

    # ---- 확인 ----
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE'", (DB_NAME,))
    n_tables = cur.fetchone()[0]
    cur.execute("SELECT zone, COUNT(*) FROM mood_words GROUP BY zone ORDER BY zone")
    zones = dict(cur.fetchall())
    print("\n===== Result =====")
    print(f"Tables: {n_tables} (expected {EXPECTED_TABLES})", "OK" if n_tables == EXPECTED_TABLES else "<- count differs, please check")
    print(f"mood_words: 100 rows, per zone {zones}", "OK" if sum(zones.values()) == 100 and all(v == 25 for v in zones.values()) else "<- each zone must have 25")
    if a.seed:
        cur.execute("SELECT COUNT(*) FROM users"); u = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM diary_entries"); d = cur.fetchone()[0]
        print(f"Fake users: {u}, diaries: {d}")
    print("Next: put DB_HOST / DB_USER / DB_PASSWORD / DB_NAME=moodnote in the API .env.")
    conn.close()


if __name__ == "__main__":
    main()
