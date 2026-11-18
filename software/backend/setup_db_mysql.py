"""MoodNote DB 구축 스크립트 (MySQL / MariaDB)

한 번 실행하면 아래를 순서대로 한다.
  1) schema_mysql.sql 로 DB와 테이블 11개 + 뷰 1개를 만든다.
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
EXPECTED_TABLES = 11  # users, user_profile, relationships, mood_words, diary_entries, ai_feedback,
                      # daily_condition, menstrual_cycles, self_model, safety_events, consents


def parse_args():
    p = argparse.ArgumentParser(description="MoodNote DB 구축")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=3306)
    p.add_argument("--user", default="root", help="DB를 만들 수 있는 관리자 계정 (기본 root)")
    p.add_argument("--words", default=os.path.join(HERE, "mood_words.csv"), help="구글 시트 mood_words_out 탭을 받은 CSV")
    p.add_argument("--seed", action="store_true", help="개발용 가짜 데이터도 넣기")
    p.add_argument("--app-user", default=None, help="API가 쓸 계정 이름 (예: moodnote_app)")
    p.add_argument("--app-host", default="localhost", help="그 계정이 접속할 수 있는 위치 (기본 localhost)")
    p.add_argument("--reset", action="store_true", help="기존 moodnote DB를 지우고 다시 만들기")
    return p.parse_args()


def fail(msg):
    sys.exit(f"\n[중단] {msg}")


def load_words(path):
    """CSV를 읽어 검사한 뒤 INSERT용 튜플 목록으로 돌려준다."""
    if not os.path.exists(path):
        fail(f"{path} 파일이 없어요. 구글 시트의 mood_words_out 탭을 CSV로 내려받아 mood_words.csv 이름으로 이 폴더에 넣어 주세요.")
    with open(path, encoding="utf-8-sig", newline="") as f:  # utf-8-sig: 엑셀이 붙이는 BOM 제거
        rows = list(csv.DictReader(f))
    need = ["id", "word_ko", "word_en", "grid_row", "grid_col", "energy", "pleasantness", "zone"]
    if not rows or any(c not in rows[0] for c in need):
        fail(f"CSV의 첫 줄(열 이름)이 {need} 이어야 해요. 지금은 {list(rows[0].keys()) if rows else '비어 있음'}")
    if len(rows) != 100:
        fail(f"단어는 100행이어야 해요. 지금 {len(rows)}행이에요.")
    out, problems = [], []
    for r in rows:
        ko = r["word_ko"].strip()          # '겁먹은 ' 처럼 뒤에 붙은 공백 제거
        en = r["word_en"].strip() or None
        if not ko:
            problems.append(f"id {r['id']}: 한국어 단어가 비어 있어요")
        out.append((int(r["id"]), ko, en, int(r["grid_row"]), int(r["grid_col"]),
                    int(r["energy"]), int(r["pleasantness"]), r["zone"].strip()))
    if problems:
        fail("단어 시트에 빈 칸이 있어요:\n  " + "\n  ".join(problems))
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
    print(f"서버 버전: {ver}")
    if "mariadb" in ver.lower():
        print("  (MariaDB입니다. 개발에는 괜찮지만 MySQL과 완전히 같지는 않아요.)")
        return
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", ver)
    if m and tuple(map(int, m.groups())) < (8, 0, 16):
        fail("MySQL 8.0.16 이상이 필요해요. 그 아래는 CHECK 제약이 무시돼요.")


def main():
    a = parse_args()
    for fn in ["schema_mysql.sql"] + (["seed_dev_mysql.sql"] if a.seed else []):
        if not os.path.exists(os.path.join(HERE, fn)):
            fail(f"{fn} 파일이 이 폴더에 없어요.")
    words = load_words(a.words)  # DB를 건드리기 전에 CSV부터 검사한다

    pw = os.environ.get("DB_ADMIN_PASSWORD") or getpass.getpass(f"{a.user} 계정 비밀번호: ")
    try:
        conn = pymysql.connect(host=a.host, port=a.port, user=a.user, password=pw,
                               charset="utf8mb4", client_flag=CLIENT.MULTI_STATEMENTS, autocommit=True)
    except pymysql.err.OperationalError as e:
        fail(f"DB에 접속하지 못했어요: {e}\n  MySQL이 켜져 있는지, 주소/포트/계정/비밀번호가 맞는지 확인해 주세요.")
    cur = conn.cursor()
    check_version(cur)

    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s", (DB_NAME,))
    existing = cur.fetchone()[0]
    if existing:
        if not a.reset:
            fail(f"'{DB_NAME}' DB에 이미 테이블이 {existing}개 있어요. 처음부터 다시 만들려면 --reset 을 붙이세요. (데이터가 모두 사라져요)")
        if input(f"'{DB_NAME}' DB의 모든 데이터를 지웁니다. 계속하려면 '{DB_NAME} 삭제'를 입력: ").strip() != f"{DB_NAME} 삭제":
            fail("입력이 달라서 취소했어요. 아무것도 지우지 않았어요.")
        cur.execute(f"DROP DATABASE `{DB_NAME}`")
        print("기존 DB를 지웠어요.")

    print("1) 스키마 실행 …")
    run_script(cur, os.path.join(HERE, "schema_mysql.sql"))

    print("2) 무드 단어 100개 넣기 …")
    cur.execute(f"USE `{DB_NAME}`")
    cur.executemany(
        "INSERT INTO mood_words (id, word_ko, word_en, grid_row, grid_col, energy, pleasantness, zone) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", words)

    if a.seed:
        print("3) 개발용 가짜 데이터 넣기 …")
        run_script(cur, os.path.join(HERE, "seed_dev_mysql.sql"))

    if a.app_user:
        app_pw = os.environ.get("DB_APP_PASSWORD") or getpass.getpass(f"API용 계정 '{a.app_user}' 의 새 비밀번호: ")
        if len(app_pw) < 8:
            fail("API 계정 비밀번호는 8자 이상으로 해 주세요. (DB와 스키마는 이미 만들어졌어요)")
        who = f"`{a.app_user}`@%s"
        cur.execute(f"CREATE USER IF NOT EXISTS {who} IDENTIFIED BY %s", (a.app_host, app_pw))
        cur.execute(f"ALTER USER {who} IDENTIFIED BY %s", (a.app_host, app_pw))
        cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{DB_NAME}`.* TO {who}", (a.app_host,))
        print(f"4) API용 계정 '{a.app_user}'@'{a.app_host}' 생성 (이 DB에 대해 조회/추가/수정/삭제만 가능)")

    # ---- 확인 ----
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE'", (DB_NAME,))
    n_tables = cur.fetchone()[0]
    cur.execute("SELECT zone, COUNT(*) FROM mood_words GROUP BY zone ORDER BY zone")
    zones = dict(cur.fetchall())
    print("\n===== 결과 =====")
    print(f"테이블 {n_tables}개 (기대값 {EXPECTED_TABLES})", "OK" if n_tables == EXPECTED_TABLES else "<- 숫자가 달라요, 확인 필요")
    print(f"mood_words 100행, 영역별 {zones}", "OK" if sum(zones.values()) == 100 and all(v == 25 for v in zones.values()) else "<- 영역마다 25개여야 해요")
    if a.seed:
        cur.execute("SELECT COUNT(*) FROM users"); u = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM diary_entries"); d = cur.fetchone()[0]
        print(f"가짜 사용자 {u}명, 일기 {d}개")
    print("다음: API의 .env 에 DB_HOST / DB_USER / DB_PASSWORD / DB_NAME=moodnote 를 넣으세요.")
    conn.close()


if __name__ == "__main__":
    main()
