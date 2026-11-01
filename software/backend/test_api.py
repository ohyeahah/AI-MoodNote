"""API 테스트.  실행:  python -m pytest -v
주의: 실제 DB(moodnote)에 pytest_ 로 시작하는 임시 사용자를 만들었다가 테스트가 끝나면 지운다.
      운영 DB 에서는 절대 돌리지 않는다."""
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
    with app.app_context(), db_cursor() as cur:         # 테스트가 만든 사용자 삭제 (딸린 데이터도 CASCADE 로 삭제)
        cur.execute("DELETE FROM users WHERE login_id LIKE 'pytest\\_%'")


def new_user(client, consents=("diary_storage",)):
    """임시 사용자를 만들고 로그인해서 (헤더, 아이디)를 돌려준다."""
    login_id = "pytest_" + uuid.uuid4().hex[:8]
    assert client.post("/api/auth/signup", json={"login_id": login_id, "nickname": "테스터",
                                                 "password": "password123"}).status_code == 201
    token = client.post("/api/auth/login", json={"login_id": login_id, "password": "password123"}).get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for c in consents:
        assert client.put(f"/api/consents/{c}", headers=headers, json={"granted": True, "version": "v1"}).status_code == 200
    return headers, login_id


def test_health_and_unknown_route(client):
    assert client.get("/api/health").get_json()["db"] == "connected"
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.get_json()["success"] is False


def test_mood_words(client):
    words = client.get("/api/mood-words").get_json()["mood_words"]
    assert len(words) == 100
    assert {"grid_row", "grid_col", "energy", "pleasantness", "zone"} <= set(words[0])


def test_auth(client):
    _, login_id = new_user(client, consents=())
    dup = client.post("/api/auth/signup", json={"login_id": login_id, "nickname": "x", "password": "password123"})
    assert dup.status_code == 409
    bad = client.post("/api/auth/login", json={"login_id": login_id, "password": "wrongwrong"})
    assert bad.status_code == 401
    assert client.post("/api/auth/signup", json={"login_id": "a b", "nickname": "x", "password": "password123"}).status_code == 400
    assert client.get("/api/diaries").status_code == 401


def test_consent_gate_and_history(client):
    h, _ = new_user(client, consents=())
    assert client.post("/api/diaries", headers=h, json={"content": "hi"}).status_code == 403
    state = client.get("/api/consents", headers=h).get_json()["consents"]
    assert len(state) == 6 and not any(v["granted"] for v in state.values())
    client.put("/api/consents/diary_storage", headers=h, json={"granted": True, "version": "v1"})
    assert client.post("/api/diaries", headers=h, json={"content": "hi"}).status_code == 201
    client.put("/api/consents/diary_storage", headers=h, json={"granted": False})
    assert client.post("/api/diaries", headers=h, json={"content": "hi"}).status_code == 403
    assert client.put("/api/consents/bogus", headers=h, json={"granted": True, "version": "v1"}).status_code == 400


def test_diary_flow(client):
    h, _ = new_user(client)
    text = "오늘은 발표가 있어서 긴장했다"
    r = client.post("/api/diaries", headers=h, json={"content": text, "mood_word_id": 11, "trigger_event": "발표",
                                                     "automatic_thought": "망치면 어쩌지"})
    assert r.status_code == 201
    did = r.get_json()["diary_id"]

    with app.app_context(), db_cursor() as cur:         # DB 에 평문이 아니라 암호문이 들어갔는지
        cur.execute("SELECT content, trigger_event FROM diary_entries WHERE id=%s", (did,))
        row = cur.fetchone()
        assert text not in row["content"] and "발표" not in row["trigger_event"]

    d = client.get(f"/api/diaries/{did}", headers=h).get_json()["diary"]
    assert d["content"] == text and d["trigger_event"] == "발표" and d["mood"]["id"] == 11
    assert d["entry_date"] == today_kst().isoformat()

    voice = client.post("/api/diaries", headers=h, json={"content": "음성 메모", "source": "voice"})
    vid = voice.get_json()["diary_id"]                  # 무드 단어 없이 저장되고
    assert client.get(f"/api/diaries/{vid}", headers=h).get_json()["diary"]["mood"] is None
    assert client.patch(f"/api/diaries/{vid}", headers=h, json={"mood_word_id": 45}).status_code == 200   # 나중에 붙인다
    assert client.get(f"/api/diaries/{vid}", headers=h).get_json()["diary"]["mood"]["id"] == 45
    assert client.patch(f"/api/diaries/{vid}", headers=h, json={"mood_word_id": 999}).status_code == 400
    assert client.patch(f"/api/diaries/{vid}", headers=h, json={}).status_code == 400

    assert len(client.get("/api/diaries", headers=h).get_json()["diaries"]) == 2
    assert client.post("/api/diaries", headers=h, json={"content": "x", "mood_word_id": 999}).status_code == 400
    assert client.post("/api/diaries", headers=h, json={"content": "x", "source": "bad"}).status_code == 400
    future = (today_kst() + timedelta(days=3)).isoformat()
    assert client.post("/api/diaries", headers=h, json={"content": "x", "entry_date": future}).status_code == 400

    other, _ = new_user(client)                         # 남의 일기는 보이지도 지워지지도 않는다
    assert client.get(f"/api/diaries/{did}", headers=other).status_code == 404
    assert client.delete(f"/api/diaries/{did}", headers=other).status_code == 404
    assert client.delete(f"/api/diaries/{did}", headers=h).status_code == 200
    assert client.get(f"/api/diaries/{did}", headers=h).status_code == 404


def test_daily_condition_upsert(client):
    h, _ = new_user(client)
    d = today_kst().isoformat()
    assert client.put("/api/daily-conditions", headers=h, json={"sleep_hours": 6.5, "sleep_score": 3}).status_code == 200
    assert client.put("/api/daily-conditions", headers=h, json={"sleep_hours": 7.25, "meal_count": 3}).status_code == 200
    rows = client.get(f"/api/daily-conditions?from={d}&to={d}", headers=h).get_json()["conditions"]
    assert len(rows) == 1 and rows[0]["sleep_hours"] == 7.25 and rows[0]["meal_count"] == 3 and rows[0]["sleep_score"] is None
    assert rows[0]["source"] == "self"
    assert client.put("/api/daily-conditions", headers=h, json={"sleep_score": 9}).status_code == 400
    assert client.put("/api/daily-conditions", headers=h, json={}).status_code == 400


def test_cycles(client):
    h, _ = new_user(client)
    assert client.get("/api/cycles", headers=h).status_code == 403          # cycle_tracking 동의 전
    client.put("/api/consents/cycle_tracking", headers=h, json={"granted": True, "version": "v1"})
    assert client.get("/api/cycles/summary", headers=h).get_json()["summary"] is None

    t = today_kst()
    starts = [t - timedelta(days=days) for days in (70, 42, 14)]            # 28일 간격
    ids = []
    for s in starts:
        r = client.post("/api/cycles", headers=h, json={"start_date": s.isoformat(),
                                                        "end_date": (s + timedelta(days=4)).isoformat()})
        assert r.status_code == 201
        ids.append(r.get_json()["cycle_id"])
    assert client.post("/api/cycles", headers=h, json={"start_date": starts[0].isoformat()}).status_code == 409
    assert client.post("/api/cycles", headers=h, json={"start_date": (t + timedelta(days=1)).isoformat()}).status_code == 400
    assert client.post("/api/cycles", headers=h, json={"start_date": t.isoformat(),
                                                       "end_date": (t - timedelta(days=1)).isoformat()}).status_code == 400

    s = client.get("/api/cycles/summary", headers=h).get_json()["summary"]
    assert s["cycle_day"] == 15 and s["average_cycle_length"] == 28 and s["average_period_length"] == 5
    assert s["next_start_estimate"] == (starts[-1] + timedelta(days=28)).isoformat()
    assert client.patch(f"/api/cycles/{ids[-1]}", headers=h, json={"end_date": None}).status_code == 200
    assert client.delete(f"/api/cycles/{ids[0]}", headers=h).status_code == 200
    assert len(client.get("/api/cycles", headers=h).get_json()["cycles"]) == 2


def test_graph(client):
    h, _ = new_user(client)
    client.post("/api/diaries", headers=h, json={"content": "비밀 내용", "mood_word_id": 11})    # 2행 1열: 에너지 9, 쾌적함 1
    client.post("/api/diaries", headers=h, json={"content": "또 다른 내용", "mood_word_id": 100})  # 에너지 1, 쾌적함 10
    client.put("/api/daily-conditions", headers=h, json={"sleep_hours": 7})
    r = client.get("/api/mood/graph", headers=h)
    g = r.get_json()
    assert len(g["days"]) == 1 and g["days"][0]["avg_energy"] == 5.0 and g["days"][0]["avg_pleasantness"] == 5.5
    assert g["days"][0]["condition"]["sleep_hours"] == 7
    assert "비밀 내용" not in r.get_data(as_text=True)             # 그래프에는 일기 본문이 없다
    assert client.get("/api/mood/graph?from=2026-12-01&to=2026-11-01", headers=h).status_code == 400


def test_export_and_delete_account(client):
    h, login_id = new_user(client, consents=("diary_storage", "cycle_tracking"))
    client.post("/api/diaries", headers=h, json={"content": "내보낼 일기", "mood_word_id": 5})
    client.post("/api/cycles", headers=h, json={"start_date": today_kst().isoformat()})
    for c in ("diary_storage", "cycle_tracking"):                     # 동의를 모두 철회해도
        client.put(f"/api/consents/{c}", headers=h, json={"granted": False})
    r = client.get("/api/users/me/export", headers=h)                 # 내보내기는 된다
    body = r.get_data(as_text=True)
    assert r.status_code == 200 and "내보낼 일기" in body and "password_hash" not in body
    data = r.get_json()["data"]
    assert len(data["diaries"]) == 1 and len(data["menstrual_cycles"]) == 1 and len(data["consents"]) == 2

    uid = client.get("/api/users/me", headers=h).get_json()["user"]["id"]
    assert client.delete("/api/users/me", headers=h, json={"password": "wrongwrong"}).status_code == 401
    assert client.delete("/api/users/me", headers=h, json={"password": "password123"}).status_code == 200
    with app.app_context(), db_cursor() as cur:             # 사용자와 딸린 데이터가 모두 사라졌는지
        left = 0
        for table in ("users", "diary_entries", "menstrual_cycles", "consents"):
            col = "id" if table == "users" else "user_id"
            cur.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE {col}=%s", (uid,))
            left += cur.fetchone()["n"]
        assert left == 0
    assert client.get("/api/users/me", headers=h).status_code == 404
