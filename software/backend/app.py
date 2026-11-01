"""서버 시작점. 설정을 읽고, 각 파일의 기능을 붙이고, 오류 응답 모양을 통일한다.
실행:  python app.py"""
import os
from datetime import date, datetime
from decimal import Decimal

from cryptography.fernet import Fernet
from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException

import account, auth, diary, tracking
from common import APIError, db_cursor, error_response, now_kst
from config import Config


def _json_default(o):
    """날짜와 소수는 jsonify 가 기본으로 알맞게 못 바꾸므로 직접 바꾼다."""
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"JSON 으로 바꿀 수 없는 값: {type(o)}")


class MoodJSON(DefaultJSONProvider):
    default = staticmethod(_json_default)
    ensure_ascii = False        # 한글을 \uXXXX 가 아니라 그대로 보낸다
    sort_keys = False


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.json = MoodJSON(app)
    app.extensions["fernet"] = Fernet(app.config["ENCRYPTION_KEY"].encode())   # 키가 잘못됐으면 여기서 바로 멈춘다
    CORS(app, origins=app.config["CORS_ORIGINS"])

    jwt = JWTManager(app)

    @jwt.unauthorized_loader
    def _no_token(reason):
        return error_response("AUTH_REQUIRED", "로그인이 필요합니다.", 401)

    @jwt.invalid_token_loader
    def _bad_token(reason):
        return error_response("INVALID_TOKEN", "유효하지 않은 로그인 정보입니다.", 401)

    @jwt.expired_token_loader
    def _expired(header, payload):
        return error_response("TOKEN_EXPIRED", "로그인이 만료되었습니다. 다시 로그인해 주세요.", 401)

    for module in (auth, diary, tracking, account):
        app.register_blueprint(module.bp)

    @app.get("/api/health")
    def health():
        try:
            with db_cursor() as cur:
                cur.execute("SELECT 1")
            db = "connected"
        except Exception:
            app.logger.exception("health check: DB 연결 실패")
            db = "disconnected"        # 자세한 오류는 화면이 아니라 서버 로그에만 남긴다
        return jsonify({"status": "ok", "db": db, "timestamp": now_kst()})

    @app.errorhandler(APIError)
    def _api_error(e):
        return error_response(e.code, e.message, e.status_code)

    @app.errorhandler(HTTPException)
    def _http_error(e):                # 없는 주소(404), 잘못된 방식(405) 등도 같은 JSON 모양으로
        return error_response(e.name.upper().replace(" ", "_"), e.description, e.code)

    @app.errorhandler(Exception)
    def _unexpected(e):
        app.logger.exception("처리되지 않은 오류")
        return error_response("INTERNAL_SERVER_ERROR", "서버 오류가 발생했어요. 잠시 후 다시 시도해 주세요.", 500)

    return app


app = create_app()

if __name__ == "__main__":
    # 맥은 5000번 포트를 AirPlay 가 쓰고 있어서 5001 을 쓴다. debug 는 켜지 않는다. (켜면 오류 화면에서 코드를 실행할 수 있다)
    app.run(host=os.getenv("FLASK_HOST", "127.0.0.1"), port=int(os.getenv("FLASK_PORT", "5001")), debug=False)
