"""여러 파일이 같이 쓰는 도구 모음: DB 연결, 에러, 암호화, 동의 확인, 입력 검사."""
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pymysql
from cryptography.fernet import InvalidToken
from flask import current_app, jsonify, request

KST = ZoneInfo("Asia/Seoul")

# 스키마의 consents.consent_type CHECK 와 같은 목록이어야 한다.
CONSENT_TYPES = ("diary_storage", "voice_processing", "ai_counseling",
                 "expert_export", "ai_training", "cycle_tracking")


# ---------- 시간 ----------
def now_kst():
    return datetime.now(KST)


def today_kst():
    """서버가 어느 나라에 있든 '한국 기준 오늘'을 돌려준다."""
    return now_kst().date()


# ---------- 에러 ----------
class APIError(Exception):
    """사용자에게 보여줄 오류. app.py 의 error handler 가 JSON 으로 바꿔 준다."""

    def __init__(self, message, code="INVALID_INPUT", status_code=400):
        super().__init__(message)
        self.message, self.code, self.status_code = message, code, status_code


def error_response(code, message, status):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status


# ---------- DB ----------
@contextmanager
def db_cursor():
    """with db_cursor() as cur: 로 쓴다. 정상 종료하면 저장(commit), 오류가 나면 되돌리고(rollback) 연결을 닫는다."""
    cfg = current_app.config
    conn = pymysql.connect(
        host=cfg["DB_HOST"], port=cfg["DB_PORT"], user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"], database=cfg["DB_NAME"], charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,    # 결과를 {"열이름": 값} 모양으로 받는다
        autocommit=False,
        init_command="SET time_zone = '+09:00'",   # created_at 등을 서버 위치와 상관없이 한국 시간으로
    )
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def is_duplicate_error(exc):
    """UNIQUE 제약에 걸린 오류인지 (MySQL 오류번호 1062)."""
    return isinstance(exc, pymysql.err.IntegrityError) and exc.args and exc.args[0] == 1062


# ---------- 암호화 ----------
def encrypt(text):
    if text is None:
        return None
    return current_app.extensions["fernet"].encrypt(text.encode()).decode()


def decrypt(token):
    if token is None:
        return None
    try:
        return current_app.extensions["fernet"].decrypt(token.encode()).decode()
    except InvalidToken:
        return "[복호화 실패]"


# ---------- 동의 ----------
def require_consent(cur, user_id, consent_type):
    """동의 기록이 있고 철회되지 않았을 때만 통과. 기록이 없으면 '동의 안 함'이다."""
    cur.execute(
        "SELECT 1 FROM consents WHERE user_id=%s AND consent_type=%s AND revoked_at IS NULL LIMIT 1",
        (user_id, consent_type))
    if not cur.fetchone():
        raise APIError(f"'{consent_type}' 동의가 필요합니다.", "CONSENT_REQUIRED", 403)


# ---------- 입력 검사 ----------
def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError("요청 본문이 올바른 JSON 객체가 아니에요.")
    return data


def req_text(data, key, min_len=1, max_len=20000):
    v = data.get(key)
    if not isinstance(v, str) or not (min_len <= len(v.strip()) <= max_len):
        raise APIError(f"'{key}' 는 {min_len}~{max_len}자 문자열이어야 해요.")
    return v.strip()


def opt_text(data, key, max_len=5000):
    v = data.get(key)
    if v is None:
        return None
    if not isinstance(v, str) or len(v.strip()) > max_len:
        raise APIError(f"'{key}' 는 {max_len}자 이하 문자열이어야 해요.")
    return v.strip() or None


def opt_number(data, key, lo, hi, integer=True):
    v = data.get(key)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise APIError(f"'{key}' 는 숫자여야 해요.")
    if integer and v != int(v):
        raise APIError(f"'{key}' 는 정수여야 해요.")
    if not (lo <= v <= hi):
        raise APIError(f"'{key}' 는 {lo}~{hi} 사이여야 해요.")
    return int(v) if integer else round(float(v), 2)


def parse_date(value, field, allow_future=False):
    if value in (None, ""):
        return None
    try:
        d = date.fromisoformat(str(value))
    except ValueError:
        raise APIError(f"'{field}' 는 YYYY-MM-DD 형식이어야 해요.")
    if not allow_future and d > today_kst():
        raise APIError(f"'{field}' 는 미래 날짜일 수 없어요.")
    return d


def date_range(args, default_days=30, max_days=366):
    """?from=2026-10-01&to=2026-10-31 을 읽는다. 없으면 최근 default_days 일."""
    end = parse_date(args.get("to"), "to") or today_kst()
    start = parse_date(args.get("from"), "from") or (end - timedelta(days=default_days - 1))
    if start > end:
        raise APIError("'from' 은 'to' 보다 늦을 수 없어요.")
    if (end - start).days > max_days:
        raise APIError(f"조회 기간은 최대 {max_days}일까지예요.")
    return start, end


def page_args(args, default=30, maximum=100):
    try:
        limit = int(args.get("limit", default))
        offset = int(args.get("offset", 0))
    except ValueError:
        raise APIError("limit 과 offset 은 정수여야 해요.")
    if not (1 <= limit <= maximum) or offset < 0:
        raise APIError(f"limit 은 1~{maximum}, offset 은 0 이상이어야 해요.")
    return limit, offset
