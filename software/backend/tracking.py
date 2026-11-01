"""하루 컨디션 기록, 생리주기 기록과 요약."""
import uuid
from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from common import (APIError, date_range, db_cursor, is_duplicate_error, json_body, opt_number,
                    parse_date, require_consent, today_kst)

bp = Blueprint("tracking", __name__)

# 칸 이름 -> (최솟값, 최댓값, 정수 여부). 스키마의 CHECK 와 같은 범위다.
CONDITION_FIELDS = {
    "sleep_hours": (0, 24, False), "sleep_score": (1, 5, True), "meal_count": (0, 10, True),
    "appetite_score": (1, 5, True), "bowel_score": (1, 5, True),
    "exercise_minutes": (0, 1440, True), "caffeine_cups": (0, 20, True),
}


@bp.put("/api/daily-conditions")
@jwt_required()
def save_condition():
    """그날 기록을 통째로 덮어쓴다. 안 보낸 칸은 비워진다. source 는 서버가 'self' 로 고정한다.
    (워치 값은 나중에 서버 쪽 동기화로만 들어오게 해서, 사용자가 워치 값을 흉내 낼 수 없게 한다.)"""
    user_id = get_jwt_identity()
    data = json_body()
    log_date = parse_date(data.get("log_date"), "log_date") or today_kst()
    values = {k: opt_number(data, k, lo, hi, integer) for k, (lo, hi, integer) in CONDITION_FIELDS.items()}
    if all(v is None for v in values.values()):
        raise APIError("최소 한 가지 항목은 입력해야 해요.")

    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        cur.execute("SELECT id FROM daily_condition WHERE user_id=%s AND log_date=%s AND source='self'",
                    (user_id, log_date))
        row = cur.fetchone()
        if row:
            sets = ", ".join(f"{k}=%s" for k in values)        # k 는 위 고정 목록의 이름뿐이라 안전하다
            cur.execute(f"UPDATE daily_condition SET {sets} WHERE id=%s", (*values.values(), row["id"]))
        else:
            cols = ", ".join(values)
            marks = ", ".join(["%s"] * len(values))
            cur.execute(f"INSERT INTO daily_condition (id, user_id, log_date, source, {cols}) "
                        f"VALUES (%s,%s,%s,'self',{marks})", (str(uuid.uuid4()), user_id, log_date, *values.values()))
    return jsonify({"success": True, "log_date": log_date})


@bp.get("/api/daily-conditions")
@jwt_required()
def list_conditions():
    user_id = get_jwt_identity()
    start, end = date_range(request.args)
    with db_cursor() as cur:
        require_consent(cur, user_id, "diary_storage")
        cur.execute("SELECT log_date, source, sleep_hours, sleep_score, meal_count, appetite_score, bowel_score, "
                    "exercise_minutes, caffeine_cups FROM daily_condition "
                    "WHERE user_id=%s AND log_date BETWEEN %s AND %s ORDER BY log_date, source",
                    (user_id, start, end))
        rows = cur.fetchall()
    return jsonify({"success": True, "from": start, "to": end, "conditions": rows})


# ---------------- 생리주기 (cycle_tracking 동의 필요) ----------------
@bp.post("/api/cycles")
@jwt_required()
def add_cycle():
    user_id = get_jwt_identity()
    data = json_body()
    start = parse_date(data.get("start_date"), "start_date")
    end = parse_date(data.get("end_date"), "end_date")
    if start is None:
        raise APIError("'start_date' 는 필수예요.")
    if end is not None and end < start:
        raise APIError("종료일은 시작일보다 빠를 수 없어요.")

    cycle_id = str(uuid.uuid4())
    try:
        with db_cursor() as cur:
            require_consent(cur, user_id, "cycle_tracking")
            cur.execute("INSERT INTO menstrual_cycles (id, user_id, start_date, end_date) VALUES (%s,%s,%s,%s)",
                        (cycle_id, user_id, start, end))
    except Exception as e:
        if is_duplicate_error(e):
            raise APIError("같은 시작일의 기록이 이미 있어요.", "DUPLICATE_CYCLE", 409)
        raise
    return jsonify({"success": True, "cycle_id": cycle_id}), 201


@bp.patch("/api/cycles/<cycle_id>")
@jwt_required()
def update_cycle(cycle_id):
    """주로 진행 중이던 기록에 종료일을 넣을 때 쓴다."""
    user_id = get_jwt_identity()
    data = json_body()
    if "end_date" not in data:
        raise APIError("'end_date' 를 보내 주세요. (비우려면 null)")
    end = parse_date(data["end_date"], "end_date")
    with db_cursor() as cur:
        require_consent(cur, user_id, "cycle_tracking")
        cur.execute("SELECT start_date FROM menstrual_cycles WHERE id=%s AND user_id=%s", (cycle_id, user_id))
        row = cur.fetchone()
        if not row:
            raise APIError("기록을 찾을 수 없습니다.", "NOT_FOUND", 404)
        if end is not None and end < row["start_date"]:
            raise APIError("종료일은 시작일보다 빠를 수 없어요.")
        cur.execute("UPDATE menstrual_cycles SET end_date=%s WHERE id=%s", (end, cycle_id))
    return jsonify({"success": True})


@bp.get("/api/cycles")
@jwt_required()
def list_cycles():
    user_id = get_jwt_identity()
    with db_cursor() as cur:
        require_consent(cur, user_id, "cycle_tracking")
        cur.execute("SELECT id, start_date, end_date FROM menstrual_cycles WHERE user_id=%s "
                    "ORDER BY start_date DESC", (user_id,))
        rows = cur.fetchall()
    return jsonify({"success": True, "cycles": rows})


@bp.delete("/api/cycles/<cycle_id>")
@jwt_required()
def delete_cycle(cycle_id):
    """삭제는 동의가 철회된 뒤에도 할 수 있다."""
    with db_cursor() as cur:
        cur.execute("DELETE FROM menstrual_cycles WHERE id=%s AND user_id=%s", (cycle_id, get_jwt_identity()))
        if cur.rowcount == 0:
            raise APIError("기록을 찾을 수 없습니다.", "NOT_FOUND", 404)
    return jsonify({"success": True})


@bp.get("/api/cycles/summary")
@jwt_required()
def cycle_summary():
    """기록만으로 계산한 요약. 몇 일째인지와 평균, 다음 시작 예상일. 배란이나 임신 가능성은 다루지 않는다."""
    user_id = get_jwt_identity()
    with db_cursor() as cur:
        require_consent(cur, user_id, "cycle_tracking")
        cur.execute("SELECT start_date, end_date FROM menstrual_cycles WHERE user_id=%s ORDER BY start_date",
                    (user_id,))
        rows = cur.fetchall()
    if not rows:
        return jsonify({"success": True, "summary": None})

    starts = [r["start_date"] for r in rows]
    # 시작일 사이 간격 중 15~60일만 쓴다. 기록을 빼먹어서 생긴 아주 긴 간격이 평균을 망치지 않게 하려는 것이다.
    gaps = [g for g in ((b - a).days for a, b in zip(starts, starts[1:])) if 15 <= g <= 60][-6:]
    avg_cycle = round(sum(gaps) / len(gaps)) if gaps else None
    lengths = [(r["end_date"] - r["start_date"]).days + 1 for r in rows if r["end_date"]][-6:]
    avg_period = round(sum(lengths) / len(lengths)) if lengths else None
    last = starts[-1]
    summary = {
        "last_start": last,
        "cycle_day": (today_kst() - last).days + 1,       # 마지막 시작일을 1일째로 센다
        "average_cycle_length": avg_cycle,
        "average_period_length": avg_period,
        "next_start_estimate": last + timedelta(days=avg_cycle) if avg_cycle else None,
        "cycles_logged": len(rows),
        "note": "기록을 바탕으로 한 평균 계산이며 의학적 예측이 아닙니다.",
    }
    return jsonify({"success": True, "summary": summary})
