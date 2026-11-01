"""회원가입, 로그인, 내 정보."""
import re
import uuid

from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from common import APIError, db_cursor, is_duplicate_error, json_body, req_text

bp = Blueprint("auth", __name__)
LOGIN_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{4,64}$")


@bp.post("/api/auth/signup")
def signup():
    data = json_body()
    login_id = req_text(data, "login_id", 4, 64)
    nickname = req_text(data, "nickname", 1, 50)
    password = req_text(data, "password", 8, 128)
    if not LOGIN_ID_RE.match(login_id):
        raise APIError("아이디는 영문, 숫자, _ . - 만 쓸 수 있어요 (4~64자).")

    user_id = str(uuid.uuid4())
    try:
        with db_cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, nickname, login_id, password_hash) VALUES (%s,%s,%s,%s)",
                (user_id, nickname, login_id, generate_password_hash(password, method="pbkdf2:sha256")))   # 비밀번호는 해시로만 저장
    except Exception as e:
        if is_duplicate_error(e):    # 먼저 조회하지 않고 저장을 시도해서, 동시에 가입해도 안전하다
            raise APIError("이미 존재하는 아이디입니다.", "DUPLICATE_USER", 409)
        raise
    return jsonify({"success": True, "user_id": user_id}), 201


@bp.post("/api/auth/login")
def login():
    data = json_body()
    login_id = req_text(data, "login_id", 1, 64)
    password = req_text(data, "password", 1, 128)
    with db_cursor() as cur:
        cur.execute("SELECT id, nickname, password_hash FROM users WHERE login_id=%s", (login_id,))
        user = cur.fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        raise APIError("아이디 또는 비밀번호가 올바르지 않습니다.", "AUTH_FAILED", 401)
    token = create_access_token(identity=user["id"])    # 유효 기간은 config.py 에서 정한다
    return jsonify({"success": True, "access_token": token,
                    "user": {"id": user["id"], "nickname": user["nickname"]}})


@bp.get("/api/users/me")
@jwt_required()
def me():
    with db_cursor() as cur:
        cur.execute("SELECT id, nickname, login_id, created_at FROM users WHERE id=%s", (get_jwt_identity(),))
        user = cur.fetchone()
    if not user:
        raise APIError("사용자를 찾을 수 없습니다.", "NOT_FOUND", 404)
    return jsonify({"success": True, "user": user})
