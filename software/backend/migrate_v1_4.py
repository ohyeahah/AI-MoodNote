"""moodnote DB 를 v1.3 에서 v1.4 로 올린다. (감정을 최대 3개 고를 수 있게 'picked_word_ids' 칸 추가. 기존 데이터는 지워지지 않는다)
실행:  python3 migrate_v1_4.py      (root 비밀번호를 물어본다. 두 번 실행해도 안전하다)
필요한 것: pip install pymysql"""
import getpass
import os
import sys

import pymysql


def main():
    pw = os.environ.get("DB_ADMIN_PASSWORD") or getpass.getpass("root 비밀번호: ")
    try:
        conn = pymysql.connect(host="127.0.0.1", user="root", password=pw, database="moodnote")
    except pymysql.err.OperationalError as e:
        sys.exit(f"[중단] DB에 연결하지 못했어요: {e}")

    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() "
                    "AND table_name='diary_entries' AND column_name='picked_word_ids'")
        if cur.fetchone():
            print("- picked_word_ids 칸: 이미 있어요 (건너뜀)")
        else:
            cur.execute("ALTER TABLE diary_entries ADD COLUMN picked_word_ids VARCHAR(20) NULL AFTER ai_suggested_word_ids")
            print("- picked_word_ids 칸: 추가했어요")
        # 예전 일기는 감정을 하나만 골랐으므로, 그 하나를 '고른 감정'으로 채워 둔다.
        n = cur.execute("UPDATE diary_entries SET picked_word_ids = CAST(mood_word_id AS CHAR) "
                        "WHERE mood_word_id IS NOT NULL AND picked_word_ids IS NULL")
        print(f"- 예전 일기 {n}개의 '고른 감정'을 채웠어요")
    conn.commit()
    conn.close()
    print("완료")


if __name__ == "__main__":
    main()
