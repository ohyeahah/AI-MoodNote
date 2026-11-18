"""moodnote DB 를 v1.2 에서 v1.3 으로 올린다. (물 칸, AI 추천 id 칸 추가. 기존 데이터는 지워지지 않는다)
실행:  python3 migrate_v1_3.py      (root 비밀번호를 물어본다. 두 번 실행해도 안전하다)
필요한 것: pip install pymysql"""
import getpass
import os
import sys

import pymysql


def has_column(cur, table, column):
    cur.execute("SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name=%s AND column_name=%s",
                (table, column))
    return cur.fetchone() is not None


def main():
    pw = os.environ.get("DB_ADMIN_PASSWORD") or getpass.getpass("root 비밀번호: ")
    try:
        conn = pymysql.connect(host="127.0.0.1", user="root", password=pw, database="moodnote")
    except pymysql.err.OperationalError as e:
        sys.exit(f"[중단] DB에 연결하지 못했어요: {e}")

    with conn.cursor() as cur:
        if has_column(cur, "daily_condition", "water_cups"):
            print("- 물(water_cups) 칸: 이미 있어요 (건너뜀)")
        else:
            cur.execute("ALTER TABLE daily_condition ADD COLUMN water_cups TINYINT NULL AFTER caffeine_cups")
            cur.execute("ALTER TABLE daily_condition ADD CONSTRAINT chk_dc_water CHECK (water_cups BETWEEN 0 AND 30)")
            print("- 물(water_cups) 칸: 추가했어요")

        if has_column(cur, "diary_entries", "ai_suggested_word_ids"):
            print("- AI 추천 id 칸: 이미 있어요 (건너뜀)")
        else:
            cur.execute("ALTER TABLE diary_entries ADD COLUMN ai_suggested_word_ids VARCHAR(20) NULL AFTER automatic_thought")
            print("- AI 추천 id 칸: 추가했어요")
    conn.commit()
    conn.close()
    print("완료")


if __name__ == "__main__":
    main()
