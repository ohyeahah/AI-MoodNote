"""서버 시작점. 설정을 읽고, 각 파일의 기능을 붙이고, 오류 응답 모양을 통일한다.
실행:  python app.py"""
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from cryptography.fernet import Fernet
from flask import Flask, jsonify, send_from_directory
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException, NotFound

import account, ai, auth, diary, feedback, social, tracking
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

    for module in (auth, social, diary, tracking, account, ai, feedback):
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

    # 배포할 때는 이 서버 하나가 화면(frontend/dist)까지 같이 내보낸다. (주소가 하나라서 CORS 설정이 필요 없다)
    # dist 폴더가 없으면(개발 중) 이 부분은 아무 일도 하지 않는다. 위치를 바꾸려면 .env 에 FRONTEND_DIST 를 적는다.
    dist = Path(os.getenv("FRONTEND_DIST") or Path(__file__).resolve().parent.parent / "frontend" / "dist")
    if (dist / "index.html").is_file():
        @app.get("/", defaults={"path": ""})
        @app.get("/<path:path>")
        def frontend(path):
            if path == "api" or path.startswith("api/"):
                raise NotFound()                              # 없는 API 주소는 화면이 아니라 JSON 404 로
            if path and (dist / path).is_file():
                # 브라우저가 파일을 얼마나 오래 기억할지. 기본값은 "매번 서버에 물어보기"라서, 서버가 멀면(시드니) 파일 하나마다 왕복 시간이 든다.
                # assets/ 는 내용이 바뀌면 파일 이름도 바뀌므로(해시) 1년, art/ 는 그림이라 하루 기억해도 안전하다.
                age = 31536000 if path.startswith("assets/") else 86400 if path.startswith("art/") else None
                return send_from_directory(dist, path, max_age=age)   # js, css, 그림, 글꼴 같은 파일
            return send_from_directory(dist, "index.html", max_age=0)  # /calendar 처럼 화면 주소는 모두 index.html (이건 항상 최신으로)

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
