// 백엔드와 통신하는 한 곳. 로그인 토큰(JWT)을 자동으로 붙이고, 오류를 읽기 쉬운 Error 로 바꿔 준다.
const BASE_URL = import.meta.env.VITE_API_BASE || '';
const TOKEN_KEY = 'access_token';
const AUTH_ERRORS = ['TOKEN_EXPIRED', 'INVALID_TOKEN', 'AUTH_REQUIRED'];

export const getToken = () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
export const setToken = (t) => {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* 저장이 막힌 환경 */ }
};

// 소셜 로그인이 끝나고 돌아온 주소(/auth/done#token=... 또는 #error=...)를 처리한다. 화면이 뜨기 전에 main.jsx 에서 한 번 부른다.
const SOCIAL_ERRORS = {
  cancelled: '로그인을 취소했어요.',
  state: '로그인 확인에 실패했어요. 처음부터 다시 눌러 주세요.',
  provider: '로그인 서비스와 연결하지 못했어요. 잠시 후 다시 시도해 주세요.',
  unavailable: '이 로그인은 아직 준비 중이에요. 아이디로 로그인하거나 가입해 주세요.',
};
let socialError = '';
export const getSocialError = () => socialError;
export const clearSocialError = () => { socialError = ''; };
export function consumeSocialRedirect() {
  if (window.location.pathname !== '/auth/done') return;
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  if (params.get('token')) setToken(params.get('token'));
  else socialError = SOCIAL_ERRORS[params.get('error')] || '로그인하지 못했어요. 다시 시도해 주세요.';
  window.history.replaceState(null, '', '/');      // 주소창에서 토큰을 바로 지운다
}

export const apiUrl = (endpoint) => `${BASE_URL}${endpoint}`;

function makeError(message, status, code) {
  const e = new Error(message);
  e.status = status;
  e.code = code;
  return e;
}

export async function apiRequest(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  let response;
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers });
  } catch {
    throw makeError('서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.', 0, 'NETWORK');
  }

  let data = null;
  try { data = await response.json(); } catch { /* JSON 이 아닌 응답 */ }

  if (!response.ok || !data || data.success === false) {
    const code = data?.error?.code;
    // 로그인 토큰이 만료되었거나 잘못됐으면 앱 전체에 알려서 로그인 화면으로 보낸다.
    if (token && AUTH_ERRORS.includes(code)) {
      setToken(null);
      window.dispatchEvent(new Event('auth:expired'));
    }
    throw makeError(data?.error?.message || '요청을 처리하지 못했어요.', response.status, code);
  }
  return data;
}
