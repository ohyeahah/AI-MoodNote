import React, { useEffect, useState } from 'react';
import { apiRequest, apiUrl, clearSocialError, getSocialError } from '../api/client';
import { useAuth } from '../auth/AuthContext';

// 로그인 화면: 아이디, 비밀번호, 로그인 버튼, 그 아래 소셜 로그인 3개(Google, 네이버, 카카오).
// 버튼을 누르면 서버(/api/auth/<업체>/start)가 업체의 로그인 화면으로 보낸다. 서버에 키가 없는 업체는 "준비 중"이라고 알려 준다.
// 아이콘은 각 업체 공식 색을 따라 그린 것이다. 앱을 공개하기 전에 각 업체 개발자 사이트의 공식 버튼 이미지로 바꿔야 한다.
const MARKS = {
  google: (
    <svg viewBox="0 0 48 48" width="26" height="26" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  ),
  naver: (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
      <path fill="#fff" d="M16.273 12.845 7.376 0H0v24h7.726V11.156L16.624 24H24V0h-7.727v12.845z" />
    </svg>
  ),
  kakao: (
    <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">
      <path fill="#191919" d="M12 3C6.48 3 2 6.58 2 11c0 2.84 1.87 5.33 4.69 6.75l-.96 3.5a.4.4 0 0 0 .6.44L10.5 19c.5.06 1 .1 1.5.1 5.52 0 10-3.58 10-8S17.52 3 12 3z" />
    </svg>
  ),
};
const SOCIAL = [
  { key: 'google', name: 'Google' },
  { key: 'naver', name: '네이버' },
  { key: 'kakao', name: '카카오' },
];

export default function LoginPage() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState('login');
  const [loginId, setLoginId] = useState('');
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(getSocialError);      // 소셜 로그인에서 돌아왔는데 실패했다면 그 이유
  const [ready, setReady] = useState({});                     // 서버에서 켜져 있는 소셜 로그인 {kakao: true, ...}
  const [busy, setBusy] = useState(false);
  const isLogin = mode === 'login';

  useEffect(() => {
    clearSocialError();
    apiRequest('/api/auth/providers').then((r) => setReady(r.providers)).catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setError(''); setBusy(true);
    try {
      if (isLogin) await login(loginId.trim(), password);
      else await signup(loginId.trim(), nickname.trim(), password);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const social = (s) => () => {
    if (!ready[s.key]) { setError(`${s.name} 로그인은 아직 준비 중이에요. 아이디로 로그인하거나 가입해 주세요.`); return; }
    window.location.href = apiUrl(`/api/auth/${s.key}/start`);     // 업체 로그인 화면으로 이동. 끝나면 /auth/done 으로 돌아온다.
  };

  return (
    <main className="auth login">
      <h1 className="wordmark"><img src="/art/ui/logo.png" alt="MoodNote" height="84" draggable="false" /></h1>

      <form onSubmit={submit} className="stack">
        {/* 회원가입은 닉네임 → 아이디 → 비밀번호 순서 */}
        {!isLogin && (
          <input aria-label="닉네임" placeholder="닉네임" value={nickname} onChange={(e) => setNickname(e.target.value)} required maxLength={50} />
        )}
        <input aria-label="아이디" placeholder="아이디" value={loginId} onChange={(e) => setLoginId(e.target.value)}
          autoComplete="username" required minLength={isLogin ? 1 : 4} maxLength={64} />
        <input aria-label="비밀번호" type="password" placeholder={isLogin ? '비밀번호' : '비밀번호 (8자 이상)'} value={password}
          onChange={(e) => setPassword(e.target.value)} autoComplete={isLogin ? 'current-password' : 'new-password'}
          required minLength={isLogin ? 1 : 8} maxLength={128} />
        {error && <p className="msg error" role="alert">{error}</p>}
        <button className="btn primary full" disabled={busy}>{busy ? '잠시만요…' : isLogin ? '로그인' : '가입하고 시작하기'}</button>
      </form>

      <div className="social" role="group" aria-label="다른 계정으로 로그인">
        {SOCIAL.map((s) => (
          <button key={s.key} type="button" className={`social-btn ${s.key}`} aria-label={`${s.name}로 로그인`} title={s.name} onClick={social(s)}>{MARKS[s.key]}</button>
        ))}
      </div>

      <p className="switch muted">
        {isLogin ? '계정이 없나요? ' : '이미 계정이 있나요? '}
        <button type="button" className="link" onClick={() => { setMode(isLogin ? 'signup' : 'login'); setError(''); }}>
          {isLogin ? '회원가입' : '로그인'}
        </button>
      </p>
    </main>
  );
}
