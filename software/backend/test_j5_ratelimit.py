"""J5 테스트: 로그인·회원가입 횟수 제한(Rate Limit) 및 429 한국어 응답 검증.
실행: python -m pytest -v
"""
import uuid

import pytest

from app import app
from common import db_cursor, limiter

if app.config["APP_ENV"] == "production":
    raise RuntimeError("운영 환경에서는 테스트를 돌리지 않습니다.")


@pytest.fixture
def rate_limited_client():
    app.config["TESTING"] = True
    limiter.enabled = True
    limiter.reset()
    with app.test_client() as c:
        yield c
    limiter.reset()
    with app.app_context(), db_cursor() as cur:
        cur.execute("DELETE FROM users WHERE login_id LIKE 'pytest\\_%'")


def test_login_rate_limit(rate_limited_client):
    """로그인 API는 분당 10회까지 허용하고, 11번째부터 429와 한국어 안내문을 반환해야 한다."""
    login_id = "pytest_" + uuid.uuid4().hex[:8]
    r = rate_limited_client.post(
        "/api/auth/signup",
        json={"login_id": login_id, "nickname": "리미터테스터", "password": "password123"},
    )
    assert r.status_code == 201

    # 1~10번째 로그인 시도는 정상 처리 (200 또는 비밀번호 오류 401)
    for _ in range(10):
        res = rate_limited_client.post(
            "/api/auth/login",
            json={"login_id": login_id, "password": "wrongpassword"},
        )
        assert res.status_code == 401

    # 11번째 시도는 429 차단
    blocked = rate_limited_client.post(
        "/api/auth/login",
        json={"login_id": login_id, "password": "password123"},
    )
    body = blocked.get_json()
    assert blocked.status_code == 429
    assert body["success"] is False
    assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "요청 횟수" in body["error"]["message"]


def test_signup_rate_limit(rate_limited_client):
    """회원가입 API는 분당 5회까지 허용하고, 6번째부터 429를 반환해야 한다."""
    for _ in range(5):
        uid = "pytest_" + uuid.uuid4().hex[:8]
        res = rate_limited_client.post(
            "/api/auth/signup",
            json={"login_id": uid, "nickname": "가입테스터", "password": "password123"},
        )
        assert res.status_code == 201

    uid_over = "pytest_" + uuid.uuid4().hex[:8]
    blocked = rate_limited_client.post(
        "/api/auth/signup",
        json={"login_id": uid_over, "nickname": "초과테스터", "password": "password123"},
    )
    assert blocked.status_code == 429
    assert blocked.get_json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"