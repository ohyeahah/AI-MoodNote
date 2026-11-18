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

CATEGORY_KO = {"bug": "불편한 점", "idea": "바라는 점", "praise": "좋은 점", "other": "기타"}


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
    ap = argparse.ArgumentParser(description="받은 의견 읽기")
    ap.add_argument("--all", action="store_true", help="처리한 의견도 보기")
    ap.add_argument("--csv", metavar="파일", help="CSV 로 저장")
    ap.add_argument("--done", metavar="번호", help="의견 번호(앞부분)를 '처리함'으로 표시")
    a = ap.parse_args()

    conn = connect()
    with conn.cursor() as cur:
        if a.done:
            cur.execute("SELECT id FROM feedback WHERE id LIKE %s", (a.done.replace("%", "") + "%",))
            found = cur.fetchall()
            if len(found) != 1:
                sys.exit(f"[중단] '{a.done}' 로 시작하는 의견이 {len(found)}개예요. 번호를 더 길게 써 주세요." if found
                         else f"[중단] '{a.done}' 로 시작하는 의견이 없어요.")
            cur.execute("UPDATE feedback SET status='done' WHERE id=%s", (found[0]["id"],))
            conn.commit()
            print("처리함으로 표시했어요.")
            return

        rows = fetch(cur, only_new=not (a.all or a.csv))

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:      # utf-8-sig: 엑셀에서 한글이 깨지지 않게
            w = csv.writer(f)
            w.writerow(["번호", "시각", "종류", "별점", "닉네임", "아이디", "상태", "내용"])
            for r in rows:
                w.writerow([r["id"][:8], r["created_at"], CATEGORY_KO[r["category"]], r["rating"] or "",
                            r["nickname"], r["login_id"], "처리함" if r["status"] == "done" else "새 의견", r["message"]])
        print(f"{len(rows)}개를 {a.csv} 에 저장했어요.")
        return

    if not rows:
        print("새 의견이 없어요." if not a.all else "의견이 아직 없어요.")
        return
    for r in rows:
        stars = f"  별점 {r['rating']}/5" if r["rating"] else ""
        done = "  (처리함)" if r["status"] == "done" else ""
        print(f"[{r['id'][:8]}] {r['created_at']:%Y-%m-%d %H:%M}  {CATEGORY_KO[r['category']]}{stars}  - {r['nickname']}{done}")
        print("    " + r["message"].replace("\n", "\n    "))
        print()
    print(f"총 {len(rows)}개. 처리한 의견은 python3 show_feedback.py --done 번호 로 표시해요.")


if __name__ == "__main__":
    main()
