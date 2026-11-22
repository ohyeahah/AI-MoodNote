"""소셜 로그인 (카카오, 네이버, 구글).

흐름
  1) 화면의 버튼 → GET /api/auth/<업체>/start      : 무작위 state 를 쿠키에 적어 두고 업체의 로그인 화면으로 보낸다.
  2) 사용자가 업체에서 로그인·동의 → 업체가 GET /api/auth/<업체>/callback?code=...&state=... 로 돌려보낸다.
  3) 서버가 state 를 확인하고, code 를 access token 으로 바꾸고, 그 토큰으로 '업체 안에서의 사용자 번호'만 받아 온다.
  4) 그 번호가 user_identities 에 있으면 그 사용자로, 없으면 새 사용자를 만들어서 MoodNote 로그인 토큰(JWT)을 발급한다.
  5) /auth/done#token=... 으로 돌려보내면 화면이 토큰을 저장한다. (토큰을 # 뒤에 두면 서버 로그와 다른 사이트에 남지 않는다)

저장하는 것: 업체 이름 + 업체 안의 사용자 번호뿐. 이메일, 이름, 프로필 사진은 요청하지도 저장하지도 않는다.
다른 로그인 방법과 같은 사람인지 이메일로 짐작해서 합치지 않는다. (남의 계정을 가로채는 길이 되기 때문이다)
"""
import json
import secrets
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, jsonify, redirect, request
from flask_jwt_extended import create_access_token

from common import NO_PASSWORD, db_cursor, is_duplicate_error

bp = Blueprint("social", __name__)

STATE_COOKIE = "oauth_state"
DEFAULT_NICKNAME = "새로운 친구"      # 업체의 이름을 받아 오지 않으므로 기본값을 쓰고, 설정에서 바꾸게 한다.
TIMEOUT = 8                          # 업체 서버를 기다리는 최대 초

# 업체마다 주소와 응답 모양이 조금씩 다르다. user_id 는 사용자 번호가 들어 있는 위치다.
PROVIDERS = {
    "kakao": {
        "authorize": "https://kauth.kakao.com/oauth/authorize",
        "token": "https://kauth.kakao.com/oauth/token",
        "userinfo": "https://kapi.kakao.com/v2/user/me",
        "scope": None,                       # 번호(id)는 기본으로 오므로 따로 항목을 요청하지 않는다.
        "secret_required": False,
        "token_method": "POST",
        "send_state_to_token": False,
        "user_id": lambda info: info.get("id"),
    },
    "naver": {
        "authorize": "https://nid.naver.com/oauth2.0/authorize",
        "token": "https://nid.naver.com/oauth2.0/token",
        "userinfo": "https://openapi.naver.com/v1/nid/me",
        "scope": None,
        "secret_required": True,
        "token_method": "GET",
        "send_state_to_token": True,
        "user_id": lambda info: (info.get("response") or {}).get("id"),
    },
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid",                   # openid 만 요청하면 이메일 없이 사용자 번호(sub)만 온다.
        "secret_required": True,
        "token_method": "POST",
        "send_state_to_token": False,
        "user_id": lambda info: info.get("sub"),
    },
}


def _keys(provider):
    """(client_id, client_secret). 설정이 모자라면 None. 이 경우 그 업체 버튼은 '준비 중'이다."""
    cfg = current_app.config
    client_id = cfg.get(f"{provider.upper()}_CLIENT_ID", "")
    secret = cfg.get(f"{provider.upper()}_CLIENT_SECRET", "")
    if not cfg.get("PUBLIC_BASE_URL") or not client_id:
        return None
    if PROVIDERS[provider]["secret_required"] and not secret:
        return None
    return client_id, secret


def _redirect_uri(provider):
    return f"{current_app.config['PUBLIC_BASE_URL']}/api/auth/{provider}/callback"


def _back(token=None, error=None):
    """화면으로 돌려보낸다. 결과는 # 뒤에 둔다. 쿠키(state)는 한 번 쓰면 지운다."""
    frag = urlencode({"token": token} if token else {"error": error or "failed"})
    resp = redirect(f"{current_app.config['PUBLIC_BASE_URL'] or ''}/auth/done#{frag}")
    resp.delete_cookie(STATE_COOKIE, path="/api/auth")
    return resp


def _http(url, data=None, headers=None, method="POST"):
    """업체 서버에 요청하고 JSON 을 돌려준다. 시험에서는 이 함수만 바꿔 끼운다."""
    body = None
    if data is not None:
        if method == "GET":
            url = f"{url}?{urlencode(data)}"
        else:
            body = urlencode(data).encode()
    req = Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        # 업체가 돌려준 오류 내용은 서버 로그에만 남긴다. (키가 틀렸는지, Redirect URI 가 다른지 알 수 있다)
        current_app.logger.warning("social login: provider answered %s: %s", e.code, e.read()[:300])
        raise


def _provider_user_id(provider, code, state):
    """code → access token → 업체 안의 사용자 번호(문자열)."""
    spec = PROVIDERS[provider]
    client_id, secret = _keys(provider)
    form = {"grant_type": "authorization_code", "client_id": client_id, "code": code,
            "redirect_uri": _redirect_uri(provider)}
    if secret:
        form["client_secret"] = secret
    if spec["send_state_to_token"]:
        form["state"] = state
    tok = _http(spec["token"], form, method=spec["token_method"])
    access = tok.get("access_token")
    if not access:
        raise RuntimeError(f"no access_token from {provider}")
    info = _http(spec["userinfo"], headers={"Authorization": f"Bearer {access}"}, method="GET")
    pid = spec["user_id"](info)
    if pid in (None, ""):
        raise RuntimeError(f"no user id from {provider}")
    return str(pid)[:100]


def _find_or_create_user(provider, pid):
    """이 업체 계정에 연결된 사용자의 id. 없으면 새 사용자와 연결을 한 번에 만든다."""
    for _ in range(2):          # 두 번째는 '동시에 같은 사람이 처음 로그인해서 한쪽이 먼저 만든' 경우를 위한 것
        with db_cursor() as cur:
            cur.execute("SELECT user_id FROM user_identities WHERE provider=%s AND provider_user_id=%s", (provider, pid))
            row = cur.fetchone()
        if row:
            return row["user_id"]
        user_id = str(uuid.uuid4())
        try:
            with db_cursor() as cur:
                # login_id 의 ':' 는 직접 가입하는 아이디에 쓸 수 없는 글자라서, 아이디로 가입한 사람과 겹치지 않는다.
                cur.execute("INSERT INTO users (id, nickname, login_id, password_hash) VALUES (%s,%s,%s,%s)",
                            (user_id, DEFAULT_NICKNAME, f"social:{provider}:{user_id}", NO_PASSWORD))
                cur.execute("INSERT INTO user_identities (id, user_id, provider, provider_user_id) VALUES (%s,%s,%s,%s)",
                            (str(uuid.uuid4()), user_id, provider, pid))
            return user_id
        except Exception as e:
            if not is_duplicate_error(e):
                raise
    raise RuntimeError("could not create or find the social user")


@bp.get("/api/auth/providers")
def providers():
    """어느 업체 버튼이 켜져 있는지. 화면이 '준비 중' 문구를 보여줄지 정하는 데 쓴다. (키 값은 절대 내보내지 않는다)"""
    return jsonify({"success": True, "providers": {p: _keys(p) is not None for p in PROVIDERS}})


@bp.get("/api/auth/<provider>/start")
def start(provider):
    if provider not in PROVIDERS:
        return _back(error="unavailable")
    keys = _keys(provider)
    if not keys:
        return _back(error="unavailable")
    spec = PROVIDERS[provider]
    state = secrets.token_urlsafe(24)
    params = {"response_type": "code", "client_id": keys[0], "redirect_uri": _redirect_uri(provider), "state": state}
    if spec["scope"]:
        params["scope"] = spec["scope"]
    resp = redirect(f"{spec['authorize']}?{urlencode(params)}")
    # state 를 이 브라우저에 묶어 둔다. 돌아왔을 때 값이 같아야만 '내가 시작한 로그인'으로 인정한다. (남이 만든 링크로 로그인시키는 공격 방지)
    resp.set_cookie(STATE_COOKIE, state, max_age=600, httponly=True, samesite="Lax", path="/api/auth",
                    secure=current_app.config["PUBLIC_BASE_URL"].startswith("https"))
    return resp


@bp.get("/api/auth/<provider>/callback")
def callback(provider):
    if provider not in PROVIDERS or not _keys(provider):
        return _back(error="unavailable")
    if request.args.get("error"):                       # 사용자가 업체 화면에서 취소했다.
        return _back(error="cancelled")
    state, cookie = request.args.get("state", ""), request.cookies.get(STATE_COOKIE, "")
    if not state or not cookie or not secrets.compare_digest(state, cookie):
        return _back(error="state")
    code = request.args.get("code")
    if not code:
        return _back(error="provider")
    try:
        pid = _provider_user_id(provider, code, state)
        user_id = _find_or_create_user(provider, pid)
    except Exception:
        current_app.logger.exception("social login failed (%s)", provider)
        return _back(error="provider")
    return _back(token=create_access_token(identity=user_id))
