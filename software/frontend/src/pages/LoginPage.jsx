import React, { useState } from 'react';
import { useAuth } from '../auth/AuthContext';

// 로그인 화면 (손그림 스케치 기준): 아이디, 비밀번호, 로그인 버튼, 그 아래 소셜 로그인 4개(G, N, 카카오, 애플).
// 소셜 버튼의 모양은 임시다. 실제로 연결할 때는 각 회사가 정한 공식 버튼 이미지로 바꿔야 한다.
const SOCIAL = [
  { key: 'google', name: 'Google', mark: 'G' },
  { key: 'naver', name: '네이버', mark: 'N' },
  { key: 'kakao', name: '카카오', mark: '💬' },
  { key: 'apple', name: 'Apple', mark: '🍎' },
];

export default function LoginPage() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState('login');
  const [loginId, setLoginId] = useState('');
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const isLogin = mode === 'login';

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

  const social = (name) => () => setError(`${name} 로그인은 아직 준비 중이에요. 아이디로 로그인하거나 가입해 주세요.`);

  return (
    <main className="auth login">
      <h1 className="wordmark">MoodNote</h1>

      <form onSubmit={submit} className="stack">
        <input aria-label="아이디" placeholder="아이디" value={loginId} onChange={(e) => setLoginId(e.target.value)}
          autoComplete="username" required minLength={isLogin ? 1 : 4} maxLength={64} />
        {!isLogin && (
          <input aria-label="닉네임" placeholder="닉네임" value={nickname} onChange={(e) => setNickname(e.target.value)} required maxLength={50} />
        )}
        <input aria-label="비밀번호" type="password" placeholder={isLogin ? '비밀번호' : '비밀번호 (8자 이상)'} value={password}
          onChange={(e) => setPassword(e.target.value)} autoComplete={isLogin ? 'current-password' : 'new-password'}
          required minLength={isLogin ? 1 : 8} maxLength={128} />
        {error && <p className="msg error" role="alert">{error}</p>}
        <button className="btn primary full" disabled={busy}>{busy ? '잠시만요…' : isLogin ? '로그인' : '가입하고 시작하기'}</button>
      </form>

      <div className="social" role="group" aria-label="다른 계정으로 로그인">
        {SOCIAL.map((s) => (
          <button key={s.key} type="button" className="social-btn" aria-label={`${s.name}로 로그인`} title={s.name} onClick={social(s.name)}>{s.mark}</button>
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
