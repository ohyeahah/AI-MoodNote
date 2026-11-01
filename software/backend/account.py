"""동의 관리, 내 데이터 내보내기, 회원 탈퇴."""
import uuid

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash

from common import CONSENT_TYPES, APIError, db_cursor, decrypt, json_body, now_kst, req_text

bp = Blueprint("account", __name__)


@bp.get("/api/consents")
@jwt_required()
def get_consents():
    """6가지 동의 각각의 현재 상태. 기록이 없으면 granted=false (기본 off)."""
    user_id = get_jwt_identity()
    with db_cursor() as cur:
        cur.execute("SELECT consent_type, version, granted_at, revoked_at FROM consents "
                    "WHERE user_id=%s ORDER BY granted_at", (user_id,))
        rows = cur.fetchall()
    state = {t: {"granted": False, "version": None, "granted_at": None, "revoked_at": None} for t in CONSENT_TYPES}
    for r in rows:                      # 시간순이라 마지막 행이 최신 상태가 된다
        state[r["consent_type"]] = {"granted": r["revoked_at"] is None, "version": r["version"],
                                    "granted_at": r["granted_at"], "revoked_at": r["revoked_at"]}
    return jsonify({"success": True, "consents": state})


@bp.put("/api/consents/<consent_type>")
@jwt_required()
def set_consent(consent_type):
    """body: {"granted": true, "version": "v1"}.  동의하면 새 행을 추가하고, 철회하면 revoked_at 을 채운다.
    행을 지우지 않는 이유는 '언제 동의하고 언제 철회했는지' 기록이 남아야 하기 때문이다."""
    if consent_type not in CONSENT_TYPES:
        raise APIError(f"알 수 없는 동의 종류예요. {', '.join(CONSENT_TYPES)} 중 하나여야 해요.")
    user_id = get_jwt_identity()
    data = json_body()
    granted = data.get("granted")
    if not isinstance(granted, bool):
        raise APIError("'granted' 는 true 또는 false 여야 해요.")
    version = req_text(data, "version", 1, 20) if granted else None

    with db_cursor() as cur:
        cur.execute("SELECT id FROM consents WHERE user_id=%s AND consent_type=%s AND revoked_at IS NULL",
                    (user_id, consent_type))
        active = cur.fetchone()
        if granted and not active:
            cur.execute("INSERT INTO consents (id, user_id, consent_type, version) VALUES (%s,%s,%s,%s)",
                        (str(uuid.uuid4()), user_id, consent_type, version))
        elif not granted and active:
            cur.execute("UPDATE consents SET revoked_at=NOW() WHERE id=%s", (active["id"],))
    return jsonify({"success": True, "consent_type": consent_type, "granted": granted})


@bp.get("/api/users/me/export")
@jwt_required()
def export_my_data():
    """내 데이터 전체를 내려받는다. 동의가 없어도, 철회한 뒤에도 가능해야 한다."""
    user_id = get_jwt_identity()
    with db_cursor() as cur:
        cur.execute("SELECT id, nickname, login_id, created_at FROM users WHERE id=%s", (user_id,))
        user = cur.fetchone()
        if not user:
            raise APIError("사용자를 찾을 수 없습니다.", "NOT_FOUND", 404)
        cur.execute("SELECT * FROM user_profile WHERE user_id=%s", (user_id,))
        profile = cur.fetchone()
        cur.execute("SELECT * FROM diary_entries WHERE user_id=%s ORDER BY entry_date, created_at", (user_id,))
        diaries = cur.fetchall()
        cur.execute("SELECT f.* FROM ai_feedback f JOIN diary_entries d ON d.id=f.entry_id WHERE d.user_id=%s",
                    (user_id,))
        feedback = cur.fetchall()
        cur.execute("SELECT * FROM daily_condition WHERE user_id=%s ORDER BY log_date", (user_id,))
        conditions = cur.fetchall()
        cur.execute("SELECT * FROM menstrual_cycles WHERE user_id=%s ORDER BY start_date", (user_id,))
        cycles = cur.fetchall()
        cur.execute("SELECT consent_type, version, granted_at, revoked_at FROM consents WHERE user_id=%s", (user_id,))
        consents = cur.fetchall()

    for d in diaries:
        for col in ("content", "trigger_event", "automatic_thought"):
            d[col] = decrypt(d[col])
    if profile and profile.get("childhood_trauma"):
        profile["childhood_trauma"] = decrypt(profile["childhood_trauma"])
    return jsonify({"success": True, "exported_at": now_kst(), "data": {
        "user": user, "profile": profile, "diaries": diaries, "ai_feedback": feedback,
        "daily_conditions": conditions, "menstrual_cycles": cycles, "consents": consents}})


@bp.delete("/api/users/me")
@jwt_required()
def delete_account():
    """회원 탈퇴. 비밀번호를 한 번 더 확인하고, users 행을 지우면 딸린 데이터가 모두 같이 지워진다(CASCADE)."""
    user_id = get_jwt_identity()
    password = req_text(json_body(), "password", 1, 128)
    with db_cursor() as cur:
        cur.execute("SELECT password_hash FROM users WHERE id=%s", (user_id,))
        user = cur.fetchone()
        if not user:
            raise APIError("사용자를 찾을 수 없습니다.", "NOT_FOUND", 404)
        if not check_password_hash(user["password_hash"], password):
            raise APIError("비밀번호가 올바르지 않습니다.", "AUTH_FAILED", 401)
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    return jsonify({"success": True})
