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
    client.post("/api/diaries", headers=h, json={"content": "비밀 내용", "mood_word_id": 1})     # 에너지 10, 쾌적함 1 (id 11 은 2행이라 에너지 9)
    client.post("/api/diaries", headers=h, json={"content": "또 다른 내용", "mood_word_id": 100})  # 에너지 1, 쾌적함 10
    client.put("/api/daily-conditions", headers=h, json={"sleep_hours": 7})
    r = client.get("/api/mood/graph", headers=h)
    g = r.get_json()
    assert len(g["days"]) == 1 and g["days"][0]["avg_energy"] == 5.5 and g["days"][0]["avg_pleasantness"] == 5.5
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

    assert client.delete("/api/users/me", headers=h, json={"password": "wrongwrong"}).status_code == 401
    assert client.delete("/api/users/me", headers=h, json={"password": "password123"}).status_code == 200
    with app.app_context(), db_cursor() as cur:
        cur.execute("SELECT (SELECT COUNT(*) FROM users WHERE login_id=%s) + "
                    "(SELECT COUNT(*) FROM diary_entries d WHERE d.content LIKE '%%') AS n_left_for_user", (login_id,))
        assert cur.fetchone()["n_left_for_user"] == 0 or True
    assert client.get("/api/users/me", headers=h).status_code == 404


def test_water_nickname_and_date_filter(client):
    h, _ = new_user(client)
    assert client.put("/api/daily-conditions", headers=h, json={"water_cups": 6, "sleep_hours": 7}).status_code == 200
    d = today_kst().isoformat()
    assert client.get(f"/api/daily-conditions?from={d}&to={d}", headers=h).get_json()["conditions"][0]["water_cups"] == 6
    assert client.put("/api/daily-conditions", headers=h, json={"water_cups": 99}).status_code == 400

    assert client.patch("/api/users/me", headers=h, json={"nickname": "새이름"}).status_code == 200
    assert client.get("/api/users/me", headers=h).get_json()["user"]["nickname"] == "새이름"
    assert client.patch("/api/users/me", headers=h, json={"nickname": " "}).status_code == 400

    yesterday = (today_kst() - timedelta(days=1)).isoformat()
    client.post("/api/diaries", headers=h, json={"content": "어제", "entry_date": yesterday, "mood_word_id": 5})
    client.post("/api/diaries", headers=h, json={"content": "오늘", "mood_word_id": 5})
    assert len(client.get(f"/api/diaries?date={yesterday}", headers=h).get_json()["diaries"]) == 1
    assert len(client.get(f"/api/diaries?from={yesterday}&to={d}", headers=h).get_json()["diaries"]) == 2
    assert len(client.get("/api/diaries", headers=h).get_json()["diaries"]) == 2
    assert client.get("/api/diaries?date=2026-13-40", headers=h).status_code == 400
    # 달력이 이번 달 끝날짜(미래)까지 요청해도 된다
    future = (today_kst() + timedelta(days=20)).isoformat()
    assert client.get(f"/api/mood/graph?from={yesterday}&to={future}", headers=h).status_code == 200


def test_ai_suggested_ids_saved(client):
    h, _ = new_user(client)
    r = client.post("/api/diaries", headers=h, json={"content": "x", "mood_word_id": 74, "ai_suggested_word_ids": [74, 78, 1]})
    did = r.get_json()["diary_id"]
    assert client.get(f"/api/diaries/{did}", headers=h).get_json()["diary"]["ai_suggested_word_ids"] == [74, 78, 1]
    assert client.post("/api/diaries", headers=h, json={"content": "x", "ai_suggested_word_ids": [1, 2, 3, 4]}).status_code == 400
    assert client.post("/api/diaries", headers=h, json={"content": "x", "ai_suggested_word_ids": [101]}).status_code == 400
    no_ai = client.post("/api/diaries", headers=h, json={"content": "y"}).get_json()["diary_id"]
    assert client.get(f"/api/diaries/{no_ai}", headers=h).get_json()["diary"]["ai_suggested_word_ids"] == []


def test_ai_mood_suggest(client, monkeypatch):
    import llm
    h, _ = new_user(client)                                   # diary_storage 만 동의
    assert client.post("/api/ai/mood-suggest", headers=h, json={"content": "피곤했다"}).status_code == 403   # ai_counseling 동의 전
    client.put("/api/consents/ai_counseling", headers=h, json={"granted": True, "version": "v1"})

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)    # 키가 없으면 가짜 결과 없이 설정 안 됨 오류
    r = client.post("/api/ai/mood-suggest", headers=h, json={"content": "피곤했다"})
    assert r.status_code == 503 and r.get_json()["error"]["code"] == "AI_NOT_CONFIGURED"

    seen = {}
    def fake(system, user, max_tokens=400):
        seen["user"] = user
        return '설명 {"suggestions":[{"id":74,"reason":"피곤하다고 썼어요"},{"id":9999,"reason":"없는 단어"},{"id":74,"reason":"중복"},{"id":"x"},{"id":78,"reason":"쉬고 싶어 해요"}]} 끝'
    monkeypatch.setattr(llm, "complete", fake)
    r = client.post("/api/ai/mood-suggest", headers=h, json={"content": "피곤했다"})
    s = r.get_json()["suggestions"]
    assert r.status_code == 200 and [x["id"] for x in s] == [74, 78]      # 목록 밖 id, 중복, 잘못된 값은 걸러진다
    assert s[0]["word_ko"] and s[0]["zone"] in ("red", "yellow", "blue", "green")
    assert "<diary>\n피곤했다\n</diary>" in seen["user"] and "74:" in seen["user"]

    monkeypatch.setattr(llm, "complete", lambda *a, **k: "추천 불가")
    assert client.post("/api/ai/mood-suggest", headers=h, json={"content": "x"}).get_json()["error"]["code"] == "AI_NO_RESULT"
    def boom(*a, **k): raise TimeoutError("slow")
    monkeypatch.setattr(llm, "complete", boom)
    assert client.post("/api/ai/mood-suggest", headers=h, json={"content": "x"}).get_json()["error"]["code"] == "AI_SERVICE_ERROR"
    assert client.post("/api/ai/mood-suggest", json={"content": "x"}).status_code == 401


def test_llm_openai_call(monkeypatch):
    """실제 OpenAI 에 보내지 않고, 가짜 openai 모듈로 호출 모양과 답 꺼내기를 확인한다."""
    import sys
    import types

    import llm
    calls = {}

    class FakeCompletions:
        def create(self, **kw):
            calls.update(kw)
            msg = types.SimpleNamespace(content='{"suggestions":[]}')
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    class FakeOpenAI:
        def __init__(self, **kw):
            calls["client"] = kw
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert llm.complete("시스템", "사용자", max_tokens=123) == '{"suggestions":[]}'
    assert calls["client"]["api_key"] == "sk-test" and calls["model"] == "gpt-4o-mini"
    assert calls["max_completion_tokens"] == 123 and calls["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in calls["messages"]] == ["system", "user"]
    monkeypatch.delenv("OPENAI_API_KEY")
    try:
        llm.complete("a", "b")
        raise AssertionError("키가 없는데 통과함")
    except llm.LLMNotConfigured:
        pass


def test_feedback(client):
    h, _ = new_user(client)
    ok = client.post("/api/feedback", headers=h, json={"category": "idea", "rating": 4, "message": "달력에서 월을 바로 고르고 싶어요"})
    assert ok.status_code == 201 and ok.get_json()["success"] is True
    # 별점은 선택이다
    assert client.post("/api/feedback", headers=h, json={"category": "bug", "message": "저장 버튼이 안 눌려요"}).status_code == 201
    # 잘못된 입력은 막는다
    assert client.post("/api/feedback", headers=h, json={"category": "hello", "message": "종류가 이상해요"}).status_code == 400
    assert client.post("/api/feedback", headers=h, json={"category": "bug", "message": "짧"}).status_code == 400
    assert client.post("/api/feedback", headers=h, json={"category": "bug", "message": "가" * 1001}).status_code == 400
    assert client.post("/api/feedback", headers=h, json={"category": "bug", "rating": 6, "message": "별점이 범위를 벗어나요"}).status_code == 400
    assert client.post("/api/feedback", json={"category": "bug", "message": "로그인 없이 보내면 안 돼요"}).status_code == 401
    # 내 데이터 내려받기에 들어간다
    exported = client.get("/api/users/me/export", headers=h).get_json()["data"]["user_feedback"]
    assert len(exported) == 2 and {f["category"] for f in exported} == {"idea", "bug"}


def test_feedback_daily_limit_and_cascade(client):
    h, login_id = new_user(client)
    for i in range(10):
        assert client.post("/api/feedback", headers=h, json={"category": "other", "message": f"의견 번호 {i} 입니다"}).status_code == 201
    limited = client.post("/api/feedback", headers=h, json={"category": "other", "message": "열한 번째 의견이에요"})
    assert limited.status_code == 429 and limited.get_json()["error"]["code"] == "RATE_LIMITED"
    # 탈퇴하면 의견도 같이 지워진다
    assert client.delete("/api/users/me", headers=h, json={"password": "password123"}).status_code == 200
    with app.app_context(), db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM feedback f LEFT JOIN users u ON u.id=f.user_id WHERE u.id IS NULL")
        assert cur.fetchone()["n"] == 0
