"""받은 의견 읽기. 서버(또는 내 맥)의 backend 폴더에서 실행한다.
  python3 show_feedback.py                 새 의견만 (최신순)
  python3 show_feedback.py --all           처리한 것까지 전부
  python3 show_feedback.py --csv 의견.csv   엑셀로 열 수 있는 파일로 저장 (전부)
  python3 show_feedback.py --done 3a7f1c2e  그 의견을 '처리함'으로 표시 (번호 앞부분만 써도 된다)
.env 의 DB 설정을 그대로 쓴다. 의견을 보낸 사람은 닉네임으로 보인다."""
import argparse
import csv
import sys

import pymysql

from config import Config

CATEGORY_KO = {"bug": "Problem", "idea": "Wish", "praise": "Praise", "other": "Other"}   # 화면에 영어로 보이게 (서버 터미널 글꼴이 한글을 못 그리는 경우가 있다)


def connect():
    return pymysql.connect(host=Config.DB_HOST, port=Config.DB_PORT, user=Config.DB_USER, password=Config.DB_PASSWORD,
                           database=Config.DB_NAME, charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
                           init_command="SET time_zone = '+09:00'")


def fetch(cur, only_new):
    cur.execute("SELECT f.id, f.category, f.rating, f.message, f.status, f.created_at, u.nickname, u.login_id "
                "FROM feedback f JOIN users u ON u.id=f.user_id "
                + ("WHERE f.status='new' " if only_new else "") + "ORDER BY f.created_at DESC")
    return cur.fetchall()


def main():
    ap = argparse.ArgumentParser(description="Read received feedback")
    ap.add_argument("--all", action="store_true", help="also show items marked done")
    ap.add_argument("--csv", metavar="FILE", help="save as CSV")
    ap.add_argument("--done", metavar="ID", help="mark the feedback (ID prefix) as done")
    a = ap.parse_args()

    conn = connect()
    with conn.cursor() as cur:
        if a.done:
            cur.execute("SELECT id FROM feedback WHERE id LIKE %s", (a.done.replace("%", "") + "%",))
            found = cur.fetchall()
            if len(found) != 1:
                sys.exit(f"[ABORTED] {len(found)} items start with '{a.done}'. Please type a longer ID." if found
                         else f"[ABORTED] No feedback starts with '{a.done}'.")
            cur.execute("UPDATE feedback SET status='done' WHERE id=%s", (found[0]["id"],))
            conn.commit()
            print("Marked as done.")
            return

        rows = fetch(cur, only_new=not (a.all or a.csv))

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:      # utf-8-sig: 엑셀에서 한글이 깨지지 않게
            w = csv.writer(f)
            w.writerow(["id", "time", "category", "rating", "nickname", "login_id", "status", "message"])
            for r in rows:
                w.writerow([r["id"][:8], r["created_at"], CATEGORY_KO[r["category"]], r["rating"] or "",
                            r["nickname"], r["login_id"], "done" if r["status"] == "done" else "new", r["message"]])
        print(f"Saved {len(rows)} items to {a.csv}.")
        return

    if not rows:
        print("No new feedback." if not a.all else "No feedback yet.")
        return
    for r in rows:
        stars = f"  rating {r['rating']}/5" if r["rating"] else ""
        done = "  (done)" if r["status"] == "done" else ""
        print(f"[{r['id'][:8]}] {r['created_at']:%Y-%m-%d %H:%M}  {CATEGORY_KO[r['category']]}{stars}  - {r['nickname']}{done}")
        print("    " + r["message"].replace("\n", "\n    "))
        print()
    print(f"Total {len(rows)}. To mark one as done: python3 show_feedback.py --done ID")


if __name__ == "__main__":
    main()
