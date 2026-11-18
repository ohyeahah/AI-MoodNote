"""의견(피드백) 보내기. 설정 화면의 '의견 보내기'가 여기로 온다.
의견은 일기가 아니라서 암호화하지 않는다. 개발팀이 읽어야 하는 글이기 때문이다. (읽는 법: show_feedback.py)"""
import uuid

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from common import APIError, db_cursor, json_body, opt_number, req_text

bp = Blueprint("feedback", __name__)

# 스키마의 feedback.category CHECK 와 같은 목록이어야 한다.
CATEGORIES = ("bug", "idea", "praise", "other")
DAILY_LIMIT = 10            # 한 사람이 하루(24시간)에 보낼 수 있는 의견 수. 같은 글을 계속 보내는 것을 막는다.


@bp.post("/api/feedback")
@jwt_required()
def send_feedback():
    """body: {"category": "bug", "rating": 4(선택, 1~5), "message": "내용(5~1000자)"}"""
    user_id = get_jwt_identity()
    data = json_body()
    category = data.get("category")
    if category not in CATEGORIES:
        raise APIError(f"'category' 는 {', '.join(CATEGORIES)} 중 하나여야 해요.")
    rating = opt_number(data, "rating", 1, 5)
    message = req_text(data, "message", 5, 1000)

    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM feedback WHERE user_id=%s AND created_at >= NOW() - INTERVAL 1 DAY",
                    (user_id,))
        if cur.fetchone()["n"] >= DAILY_LIMIT:
            raise APIError("오늘은 의견을 많이 보내 주셨어요. 내일 또 들려 주세요.", "RATE_LIMITED", 429)
        feedback_id = str(uuid.uuid4())
        cur.execute("INSERT INTO feedback (id, user_id, category, rating, message) VALUES (%s,%s,%s,%s,%s)",
                    (feedback_id, user_id, category, rating, message))
    return jsonify({"success": True, "id": feedback_id}), 201
