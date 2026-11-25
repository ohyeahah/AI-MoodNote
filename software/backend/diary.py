"""무드 단어, 일기(저장/조회/수정/삭제), 기분 그래프."""
import math
import uuid

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from common import (APIError, date_range, db_cursor, decrypt, encrypt, json_body, opt_text,
                    page_args, parse_date, parse_word_ids, req_text, require_consent, today_kst)

bp = Blueprint("diary", __name__)

# 일기 + 무드 단어를 한 번에 가져오는 공통 조회문
DIARY_SELECT = """
    SELECT d.id, d.entry_date, d.content, d.trigger_event, d.automatic_thought, d.source, d.ai_suggested_word_ids,
           d.created_at, d.updated_at, d.mood_word_id, d.picked_word_ids, d.research_use,
           m.word_ko, m.word_en, m.grid_row, m.grid_col, m.energy, m.pleasantness, m.zone
    FROM diary_entries d
    LEFT JOIN mood_words m ON m.id = d.mood_word_id
"""


def load_words(cur):
    """100개 단어를 id 로 찾을 수 있게 한 번에 읽어 둔다. (바뀌지 않는 작은 표라서 매번 읽어도 부담이 없다)"""
    cur.execute("SELECT id, word_ko, word_en, zone, energy, pleasantness FROM mood_words")
    return {w["id"]: w for w in cur.fetchall()}


def shape_diary(r, words=None):
    """DB 행을 응답 모양으로 바꾸면서 암호화된 칸을 푼다.
    mood = 대표 감정(고른 감정들의 평균에 가장 가까운 단어. 달력·그래프가 쓴다), mood_words = 내가 고른 감정 전부(최대 3개)."""
    picked_ids = [int(i) for i in r["picked_word_ids"].split(",")] if r.get("picked_word_ids") else (
        [r["mood_word_id"]] if r["mood_word_id"] is not None else [])      # 예전에 쓴 일기는 하나만 고른 것으로 본다
    picked = [{k: words[i][k] for k in ("id", "word_ko", "word_en", "zone", "energy", "pleasantness")}
              for i in picked_ids if words and i in words]
    mood = None
    if r["mood_word_id"] is not None:
        mood = {k: r[k] for k in ("word_ko", "word_en", "grid_row", "grid_col", "energy", "pleasantness", "zone")}
        mood["id"] = r["mood_word_id"]
    return {
        "id": r["id"], "entry_date": r["entry_date"], "source": r["source"],
        "content": decrypt(r["content"]),
        "trigger_event": decrypt(r["trigger_event"]),
        "automatic_thought": decrypt(r["automatic_thought"]),
        "research_use": bool(r["research_use"]),
        "mood": mood, "mood_words": picked, "created_at": r["created_at"], "updated_at": r["updated_at"],
        "ai_suggested_word_ids": [int(i) for i in r["ai_suggested_word_ids"].split(",")] if r["ai_suggested_word_ids"] else [],
    }


def parse_mood_ids(value):
    """고른 감정 id 목록(1~3개, 서로 다른 1~100)을 검사한다."""
    if (not isinstance(value, list) or not 1 <= len(value) <= 3 or len(set(map(str, value))) != len(value)
            or any(isinstance(i, bool) or not isinstance(i, int) or not 1 <= i <= 100 for i in value)):
        raise APIError("'mood_word_ids' 는 1~100 사이의 서로 다른 정수 1~3개의 목록이어야 해요.", "INVALID_MOOD_WORD")
    return value


def nearest_word_id(points):
    """고른 감정들의 (에너지, 쾌적도) 평균에 가장 가까운 단어 id.
    무드미터는 10x10 칸이 꽉 차 있어서(id = (행-1)*10 + 열, 에너지 = 11-행, 쾌적도 = 열) 평균을 반올림하면 그 칸이 곧 가장 가까운 단어다.
    .5 는 올림한다. (예: 쾌적도 5 와 8 의 평균 6.5 → 7)"""
    avg_e = sum(e for e, _ in points) / len(points)
    avg_p = sum(p for _, p in points) / len(points)
    energy = min(10, max(1, math.floor(avg_e + 0.5)))
    pleasantness = min(10, max(1, math.floor(avg_p + 0.5)))
    return (11 - energy - 1) * 10 + pleasantness


def mood_fields(cur, data):
    """요청에서 감정 칸을 읽어 (고른 id 문자열, 대표 단어 id) 로 돌려준다. 감정 관련 항목이 없으면 None.
    mood_word_ids(목록)를 권장하고, 예전 방식의 mood_word_id(하나)도 받는다."""
    if "mood_word_ids" in data:
        ids = parse_mood_ids(data["mood_word_ids"])
    elif "mood_word_id" in data:
        if data["mood_word_id"] is None:
            return (None, None)
        check_mood_word(cur, data["mood_word_id"])
        ids = [data["mood_word_id"]]
    else:
        return None
    cur.execute(f"SELECT id, energy, pleasantness FROM mood_words WHERE id IN ({','.join(['%s'] * len(ids))})", ids)
    found = {w["id"]: (w["energy"], w["pleasantness"]) for w in cur.fetchall()}
    if len(found) != len(ids):
        raise APIError("존재하지 않는 무드 단어예요 (1~100).", "INVALID_MOOD_WORD")
    return ",".join(str(i) for i in ids), nearest_word_id([found[i] for i in ids])


def check_mood_word(cur, mood_word_id):
    if mood_word_id is None:
        return
    if isinstance(mood_word_id, bool) or not isinstance(mood_word_id, int):
        raise APIError("'mood_word_id' 는 정수여야 해요.")
    cur.execute("SELECT 1 FROM mood_words WHERE id=%s", (mood_word_id,))
    if not cur.fetchone():
        raise APIError("존재하지 않는 무드 단어예요 (1~100).", "INVALID_MOOD_WORD")


def has_research_consent(cur, user_id):
    """연구 활용 동의(consents 의 ai_training 항목)가 지금 켜져 있는지."""
    cur.execute("SELECT 1 FROM consents WHERE user_id=%s AND consent_type='ai_training' AND revoked_at IS NULL LIMIT 1", (user_id,))
    return cur.fetchone() is not None


def research_value(cur, user_id, data, creating):
    """이 일기를 연구에 써도 되는지(0/1). 보내지 않았으면 새 일기는 내 기본 선택을, 수정은 None(바꾸지 않음)을 돌려준다.
    규칙: 연구 활용 동의가 켜져 있을 때만 1 이 될 수 있다. 동의가 없으면 언제나 0 이다."""
    wants = data.get("research_use")
    if wants is not None and not isinstance(wants, bool):
        raise APIError("'research_use' 는 true 또는 false 여야 해요.")
    consented = has_research_consent(cur, user_id)
    if wants is True and not consented:
        raise APIError("연구 활용에 동의해야 일기를 연구에 쓸 수 있어요.", "CONSENT_REQUIRED", 403)
    if wants is None:
        if not creating:
            return None
        if not consented:
            return 0
        cur.execute("SELECT research_default FROM users WHERE id=%s", (user_id,))
        return int(bool(cur.fetchone()["research_default"]))
    return int(wants)


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
    ai_ids = parse_word_ids(data.get("ai_suggested_word_ids"))

    diary_id = str(uuid.uuid4())
    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        picked, mood_word_id = mood_fields(cur, data) or (None, None)     # 음성 일기는 나중에 고르므로 비워도 된다
        research = research_value(cur, user_id, data, creating=True)
        cur.execute(
            "INSERT INTO diary_entries (id, user_id, mood_word_id, picked_word_ids, entry_date, content, source, "
            "trigger_event, automatic_thought, ai_suggested_word_ids, research_use) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (diary_id, user_id, mood_word_id, picked, entry_date, encrypt(content), source,
             encrypt(trigger_event), encrypt(automatic_thought), ai_ids, research))
    return jsonify({"success": True, "diary_id": diary_id}), 201


@bp.get("/api/diaries")
@jwt_required()
def list_diaries():
    user_id = get_jwt_identity()
    limit, offset = page_args(request.args)
    # ?date=2026-11-08 (하루) 또는 ?from=&to= (기간) 로 거를 수 있다. 둘 다 없으면 전체를 최신순으로.
    where, params = "d.user_id=%s", [user_id]
    day = parse_date(request.args.get("date"), "date", allow_future=True)
    if day:
        where += " AND d.entry_date=%s"; params.append(day)
    elif request.args.get("from") or request.args.get("to"):
        start, end = date_range(request.args)
        where += " AND d.entry_date BETWEEN %s AND %s"; params += [start, end]
    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        cur.execute(DIARY_SELECT + f" WHERE {where} ORDER BY d.entry_date DESC, d.created_at DESC "
                    "LIMIT %s OFFSET %s", (*params, limit, offset))
        rows = cur.fetchall()
        words = load_words(cur)
    return jsonify({"success": True, "diaries": [shape_diary(r, words) for r in rows],
                    "limit": limit, "offset": offset})


@bp.get("/api/diaries/<diary_id>")
@jwt_required()
def get_diary(diary_id):
    user_id = get_jwt_identity()
    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        cur.execute(DIARY_SELECT + " WHERE d.id=%s AND d.user_id=%s", (diary_id, user_id))
        row = cur.fetchone()
        words = load_words(cur)
    if not row:
        raise APIError("일기를 찾을 수 없습니다.", "NOT_FOUND", 404)
    return jsonify({"success": True, "diary": shape_diary(row, words)})


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
    if "ai_suggested_word_ids" in data:
        sets.append("ai_suggested_word_ids=%s"); values.append(parse_word_ids(data["ai_suggested_word_ids"]))
    wants_mood = "mood_word_ids" in data or "mood_word_id" in data
    wants_research = "research_use" in data
    if not sets and not wants_mood and not wants_research:
        raise APIError("고칠 항목이 없어요 (content, trigger_event, automatic_thought, mood_word_ids, ai_suggested_word_ids, research_use).")

    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        cur.execute("SELECT 1 FROM diary_entries WHERE id=%s AND user_id=%s", (diary_id, user_id))
        if not cur.fetchone():
            raise APIError("일기를 찾을 수 없습니다.", "NOT_FOUND", 404)
        if wants_mood:
            picked, mood_word_id = mood_fields(cur, data)
            sets += ["mood_word_id=%s", "picked_word_ids=%s"]; values += [mood_word_id, picked]
        if wants_research:
            sets.append("research_use=%s"); values.append(research_value(cur, user_id, data, creating=False))
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
            "exercise_minutes, caffeine_cups, water_cups FROM daily_condition "
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
