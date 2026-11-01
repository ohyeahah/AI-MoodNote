"""무드 단어, 일기(저장/조회/수정/삭제), 기분 그래프."""
import uuid

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from common import (APIError, date_range, db_cursor, decrypt, encrypt, json_body, opt_text,
                    page_args, parse_date, req_text, require_consent, today_kst)

bp = Blueprint("diary", __name__)

# 일기 + 무드 단어를 한 번에 가져오는 공통 조회문
DIARY_SELECT = """
    SELECT d.id, d.entry_date, d.content, d.trigger_event, d.automatic_thought, d.source,
           d.created_at, d.updated_at, d.mood_word_id,
           m.word_ko, m.word_en, m.grid_row, m.grid_col, m.energy, m.pleasantness, m.zone
    FROM diary_entries d
    LEFT JOIN mood_words m ON m.id = d.mood_word_id
"""


def shape_diary(r):
    """DB 행을 응답 모양으로 바꾸면서 암호화된 칸을 푼다."""
    mood = None
    if r["mood_word_id"] is not None:
        mood = {k: r[k] for k in ("word_ko", "word_en", "grid_row", "grid_col", "energy", "pleasantness", "zone")}
        mood["id"] = r["mood_word_id"]
    return {
        "id": r["id"], "entry_date": r["entry_date"], "source": r["source"],
        "content": decrypt(r["content"]),
        "trigger_event": decrypt(r["trigger_event"]),
        "automatic_thought": decrypt(r["automatic_thought"]),
        "mood": mood, "created_at": r["created_at"], "updated_at": r["updated_at"],
    }


def check_mood_word(cur, mood_word_id):
    if mood_word_id is None:
        return
    if isinstance(mood_word_id, bool) or not isinstance(mood_word_id, int):
        raise APIError("'mood_word_id' 는 정수여야 해요.")
    cur.execute("SELECT 1 FROM mood_words WHERE id=%s", (mood_word_id,))
    if not cur.fetchone():
        raise APIError("존재하지 않는 무드 단어예요 (1~100).", "INVALID_MOOD_WORD")


@bp.get("/api/mood-words")
def mood_words():
    """로그인 없이 볼 수 있는 참조 데이터. 위쪽(grid_row 1)이 에너지 높음."""
    with db_cursor() as cur:
        cur.execute("SELECT id, word_ko, word_en, grid_row, grid_col, energy, pleasantness, zone "
                    "FROM mood_words ORDER BY grid_row, grid_col")
        words = cur.fetchall()
    return jsonify({"success": True, "mood_words": words})


@bp.post("/api/diaries")
@jwt_required()
def create_diary():
    user_id = get_jwt_identity()
    data = json_body()
    content = req_text(data, "content", 1, 20000)
    source = data.get("source", "text")
    if source not in ("text", "voice"):
        raise APIError("'source' 는 text 또는 voice 여야 해요.")
    entry_date = parse_date(data.get("entry_date"), "entry_date") or today_kst()
    trigger_event = opt_text(data, "trigger_event")
    automatic_thought = opt_text(data, "automatic_thought")
    mood_word_id = data.get("mood_word_id")          # 음성 일기는 나중에 고르므로 비워도 된다

    diary_id = str(uuid.uuid4())
    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        check_mood_word(cur, mood_word_id)
        cur.execute(
            "INSERT INTO diary_entries (id, user_id, mood_word_id, entry_date, content, source, "
            "trigger_event, automatic_thought) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (diary_id, user_id, mood_word_id, entry_date, encrypt(content), source,
             encrypt(trigger_event), encrypt(automatic_thought)))
    return jsonify({"success": True, "diary_id": diary_id}), 201


@bp.get("/api/diaries")
@jwt_required()
def list_diaries():
    user_id = get_jwt_identity()
    limit, offset = page_args(request.args)
    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        cur.execute(DIARY_SELECT + " WHERE d.user_id=%s ORDER BY d.entry_date DESC, d.created_at DESC "
                    "LIMIT %s OFFSET %s", (user_id, limit, offset))
        rows = cur.fetchall()
    return jsonify({"success": True, "diaries": [shape_diary(r) for r in rows],
                    "limit": limit, "offset": offset})


@bp.get("/api/diaries/<diary_id>")
@jwt_required()
def get_diary(diary_id):
    user_id = get_jwt_identity()
    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        cur.execute(DIARY_SELECT + " WHERE d.id=%s AND d.user_id=%s", (diary_id, user_id))
        row = cur.fetchone()
    if not row:
        raise APIError("일기를 찾을 수 없습니다.", "NOT_FOUND", 404)
    return jsonify({"success": True, "diary": shape_diary(row)})


@bp.patch("/api/diaries/<diary_id>")
@jwt_required()
def update_diary(diary_id):
    """보낸 항목만 고친다. 음성 일기에 나중에 무드 단어를 붙일 때도 이걸 쓴다."""
    user_id = get_jwt_identity()
    data = json_body()
    sets, values = [], []        # 칸 이름은 아래 고정 목록에서만 가져오므로 SQL 에 안전하게 넣을 수 있다
    if "content" in data:
        sets.append("content=%s"); values.append(encrypt(req_text(data, "content", 1, 20000)))
    if "trigger_event" in data:
        sets.append("trigger_event=%s"); values.append(encrypt(opt_text(data, "trigger_event")))
    if "automatic_thought" in data:
        sets.append("automatic_thought=%s"); values.append(encrypt(opt_text(data, "automatic_thought")))
    if "mood_word_id" in data:
        sets.append("mood_word_id=%s"); values.append(data["mood_word_id"])
    if not sets:
        raise APIError("고칠 항목이 없어요 (content, trigger_event, automatic_thought, mood_word_id).")

    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        cur.execute("SELECT 1 FROM diary_entries WHERE id=%s AND user_id=%s", (diary_id, user_id))
        if not cur.fetchone():
            raise APIError("일기를 찾을 수 없습니다.", "NOT_FOUND", 404)
        if "mood_word_id" in data:
            check_mood_word(cur, data["mood_word_id"])
        cur.execute(f"UPDATE diary_entries SET {', '.join(sets)} WHERE id=%s AND user_id=%s",
                    (*values, diary_id, user_id))
    return jsonify({"success": True})


@bp.delete("/api/diaries/<diary_id>")
@jwt_required()
def delete_diary(diary_id):
    """삭제는 동의가 없어도 할 수 있다. 내 데이터를 지우는 건 언제나 가능해야 한다."""
    with db_cursor() as cur:
        cur.execute("DELETE FROM diary_entries WHERE id=%s AND user_id=%s", (diary_id, get_jwt_identity()))
        if cur.rowcount == 0:
            raise APIError("일기를 찾을 수 없습니다.", "NOT_FOUND", 404)
    return jsonify({"success": True})


@bp.get("/api/mood/graph")
@jwt_required()
def mood_graph():
    """기간별 기분 좌표 + 그날 컨디션. 일기 본문은 읽지도 내보내지도 않는다."""
    user_id = get_jwt_identity()
    start, end = date_range(request.args)
    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        cur.execute(
            "SELECT d.entry_date, d.source, m.id AS mood_word_id, m.word_ko, m.energy, m.pleasantness, m.zone "
            "FROM diary_entries d JOIN mood_words m ON m.id=d.mood_word_id "
            "WHERE d.user_id=%s AND d.entry_date BETWEEN %s AND %s ORDER BY d.entry_date, d.created_at",
            (user_id, start, end))
        moods = cur.fetchall()
        cur.execute(
            "SELECT log_date, source, sleep_hours, sleep_score, meal_count, appetite_score, bowel_score, "
            "exercise_minutes, caffeine_cups FROM daily_condition "
            "WHERE user_id=%s AND log_date BETWEEN %s AND %s", (user_id, start, end))
        conditions = cur.fetchall()

    days, zone_counts = {}, {"red": 0, "yellow": 0, "blue": 0, "green": 0}
    for r in moods:
        day = days.setdefault(r["entry_date"].isoformat(), {"entries": [], "condition": None})
        day["entries"].append({k: r[k] for k in ("mood_word_id", "word_ko", "energy", "pleasantness", "zone", "source")})
        zone_counts[r["zone"]] += 1
    for c in conditions:                      # 같은 날 직접 입력(self)과 워치(wearable)가 둘 다 있으면 직접 입력을 우선한다
        day = days.setdefault(c["log_date"].isoformat(), {"entries": [], "condition": None})
        if day["condition"] is None or c["source"] == "self":
            day["condition"] = {k: v for k, v in c.items() if k != "log_date"}
    out = []
    for d in sorted(days):
        es = days[d]["entries"]
        out.append({"date": d, "entries": es, "condition": days[d]["condition"],
                    "avg_energy": round(sum(e["energy"] for e in es) / len(es), 2) if es else None,
                    "avg_pleasantness": round(sum(e["pleasantness"] for e in es) / len(es), 2) if es else None})
    return jsonify({"success": True, "from": start, "to": end, "days": out, "zone_counts": zone_counts})
