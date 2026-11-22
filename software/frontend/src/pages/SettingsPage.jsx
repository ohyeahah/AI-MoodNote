import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { todayKST } from '../lib/dates';

// ① 설정. 닉네임, 동의, 의견 보내기, 내 데이터 내려받기, 로그아웃, 탈퇴, 공지.
const PROVIDER_NAMES = { kakao: '카카오', naver: '네이버', google: 'Google' };
const NOTICE = 'MoodNote 테스트 버전이에요. 불편한 점이나 바라는 점은 아래 "의견 보내기"로 알려 주세요.';

export default function SettingsPage() {
  const { user, consents, refresh, setConsent, logout } = useAuth();
  const [nickname, setNickname] = useState(user?.nickname || '');
  const [msg, setMsg] = useState(null);
  const [password, setPassword] = useState('');
  const [confirmText, setConfirmText] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const run = async (fn, okText) => {
    setMsg(null);
    try { await fn(); if (okText) setMsg({ type: 'ok', text: okText }); }
    catch (e) { setMsg({ type: 'error', text: e.message }); }
  };

  const saveNickname = () => run(async () => {
    await apiRequest('/api/users/me', { method: 'PATCH', body: JSON.stringify({ nickname }) });
    await refresh();
  }, '닉네임을 바꿨어요.');

  const exportData = () => run(async () => {
    const res = await apiRequest('/api/users/me/export');
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `moodnote-data-${todayKST()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }, '내 데이터를 내려받았어요.');

  const deleteAccount = () => run(async () => {
    await apiRequest('/api/users/me', { method: 'DELETE', body: JSON.stringify(user?.has_password === false ? { confirm: confirmText } : { password }) });
    logout();
  });

  const toggle = (type, label) => (
    <label className="check">
      <input type="checkbox" checked={!!consents?.[type]?.granted} onChange={(e) => run(() => setConsent(type, e.target.checked))} />
      <span>{label}</span>
    </label>
  );

  return (
    <div className="page">
      <h2>설정</h2>
      {msg && <p className={`msg ${msg.type}`} role={msg.type === 'error' ? 'alert' : 'status'}>{msg.text}</p>}

      <section className="card"><h3>공지</h3><p className="small">{NOTICE}</p></section>

      <section className="card stack">
        <h3>의견 보내기</h3>
        <p className="muted small">불편한 점, 바라는 점, 좋았던 점을 알려 주세요. 앱을 고치는 데 바로 쓸게요.</p>
        <Link to="/feedback" className="btn primary full">의견 남기기</Link>
      </section>

      <section className="card stack">
        <h3>내 정보</h3>
        <p className="muted small">
          {user?.has_password === false
            ? `로그인 방법: ${(user.login_methods || []).map((m) => PROVIDER_NAMES[m] || m).join(', ')}`
            : `아이디: ${user?.login_id}`}
        </p>
        <label>닉네임<input value={nickname} onChange={(e) => setNickname(e.target.value)} maxLength={50} /></label>
        <button type="button" className="btn secondary" disabled={!nickname.trim() || nickname.trim() === user?.nickname} onClick={saveNickname}>닉네임 저장</button>
      </section>

      <section className="card stack">
        <h3>동의</h3>
        {toggle('diary_storage', '일기와 컨디션 기록 저장 (끄면 기록과 조회가 막혀요)')}
        {toggle('ai_counseling', 'AI 감정 추천 (추천을 누를 때 일기 내용이 외부 AI로 전송돼요)')}
      </section>

      <section className="card stack">
        <h3>내 데이터</h3>
        <button type="button" className="btn secondary" onClick={exportData}>내 데이터 내려받기 (JSON)</button>
      </section>

      <button type="button" className="btn ghost full" onClick={logout}>로그아웃</button>

      <section className="card stack">
        <h3>회원 탈퇴</h3>
        <p className="muted small">일기와 컨디션을 포함한 모든 데이터가 삭제되고 되돌릴 수 없어요.</p>
        {!confirmDelete ? (
          <button type="button" className="btn ghost danger" onClick={() => setConfirmDelete(true)}>탈퇴하기</button>
        ) : (
          <>
            {user?.has_password === false ? (
              <label>확인을 위해 <b>탈퇴합니다</b> 를 입력해 주세요<input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} autoComplete="off" /></label>
            ) : (
              <label>비밀번호 확인<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>
            )}
            <button type="button" className="btn danger" disabled={user?.has_password === false ? confirmText.trim() !== '탈퇴합니다' : !password} onClick={deleteAccount}>정말 탈퇴할게요</button>
          </>
        )}
      </section>
    </div>
  );
}
