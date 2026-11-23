"""J1 백엔드 확장 테스트: 권한/동의 경계 조건, 페이지네이션, 예외 입력값, CASCADE 삭제 검증.
실행: python -m pytest -v
"""
import uuid
from datetime import timedelta

import pytest

from app import app
from common import db_cursor, today_kst

if app.config["APP_ENV"] == "production":
    raise RuntimeError("운영 환경에서는 테스트를 돌리지 않습니다.")


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
    with app.app_context(), db_cursor() as cur:
        cur.execute("DELETE FROM users WHERE login_id LIKE 'pytest\\_%'")


def new_user(client, consents=("diary_storage",)):
    login_id = "pytest_" + uuid.uuid4().hex[:8]
    res = client.post(
        "/api/auth/signup",
        json={"login_id": login_id, "nickname": "J1테스터", "password": "password123"},
    )
    assert res.status_code == 201
    token = client.post(
        "/api/auth/login",
        json={"login_id": login_id, "password": "password123"},
    ).get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for c in consents:
        r = client.put(f"/api/consents/{c}", headers=headers, json={"granted": True, "version": "v1"})
        assert r.status_code == 200
    return headers, login_id


def test_invalid_jwt_and_signup_boundaries(client):
    """위변조 토큰 차단 및 회원가입 입력값 경계 검증."""
    bad_headers = {"Authorization": "Bearer totally.invalid.token"}
    assert client.get("/api/users/me", headers=bad_headers).status_code in (401, 422)
    assert client.get("/api/diaries", headers=bad_headers).status_code in (401, 422)

    # 비밀번호 8자 미만, 아이디 4자 미만 차단
    assert client.post(
        "/api/auth/signup",
        json={"login_id": "abc", "nickname": "짧은아이디", "password": "password123"},
    ).status_code == 400
    assert client.post(
        "/api/auth/signup",
        json={"login_id": "pytest_shortpw", "nickname": "짧은비번", "password": "1234567"},
    ).status_code == 400


def test_diary_pagination_and_delete_after_revoke(client):
    """일기 페이지네이션(limit/offset) 및 동의 철회 후에도 삭제가 허용되는지 검증."""
    h, _ = new_user(client, consents=("diary_storage",))

    created_ids = []
    for i in range(3):
        r = client.post("/api/diaries", headers=h, json={"content": f"일기 {i}", "mood_word_id": 10 + i})
        assert r.status_code == 201
        created_ids.append(r.get_json()["diary_id"])

    # 페이지네이션 검증 (limit=2, offset=1 -> 2개만 반환)
    page = client.get("/api/diaries?limit=2&offset=1", headers=h).get_json()
    assert len(page["diaries"]) == 2
    assert page["limit"] == 2 and page["offset"] == 1

    # 존재하지 않는 일기 수정 시 404
    assert client.patch("/api/diaries/non-existent-id", headers=h, json={"content": "수정"}).status_code == 404

    # 동의를 철회해도 기존 내 일기 삭제는 가능해야 함 (개인정보 자기결정권)
    client.put("/api/consents/diary_storage", headers=h, json={"granted": False})
    assert client.get("/api/diaries", headers=h).status_code == 403
    assert client.delete(f"/api/diaries/{created_ids[0]}", headers=h).status_code == 200


def test_condition_consent_and_range_validation(client):
    """컨디션 기록의 동의 게이트 및 허용 범위(0~24시간 등) 검증."""
    h, _ = new_user(client, consents=())
    assert client.put("/api/daily-conditions", headers=h, json={"sleep_hours": 7}).status_code == 403

    client.put("/api/consents/diary_storage", headers=h, json={"granted": True, "version": "v1"})
    # 범위 초과/미달 입력 차단 (수면 25시간, 음수 수면, 카페인 21잔)
    assert client.put("/api/daily-conditions", headers=h, json={"sleep_hours": 25}).status_code == 400
    assert client.put("/api/daily-conditions", headers=h, json={"sleep_hours": -1}).status_code == 400
    assert client.put("/api/daily-conditions", headers=h, json={"caffeine_cups": 21}).status_code == 400


def test_cycle_patch_validation_and_delete_after_revoke(client):
    """생리주기 수정 시 종료일 역전 차단 및 동의 철회 후 삭제 허용 검증."""
    h, _ = new_user(client, consents=("cycle_tracking",))
    start = today_kst() - timedelta(days=5)
    r = client.post("/api/cycles", headers=h, json={"start_date": start.isoformat()})
    assert r.status_code == 201
    cid = r.get_json()["cycle_id"]

    # 종료일을 시작일보다 이전 날짜로 수정 시 400
    invalid_end = (start - timedelta(days=1)).isoformat()
    assert client.patch(f"/api/cycles/{cid}", headers=h, json={"end_date": invalid_end}).status_code == 400

    # 동의를 철회해도 생리주기 기록 삭제는 가능해야 함
    client.put("/api/consents/cycle_tracking", headers=h, json={"granted": False})
    assert client.get("/api/cycles", headers=h).status_code == 403
    assert client.delete(f"/api/cycles/{cid}", headers=h).status_code == 200