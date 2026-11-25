import React, { useState } from 'react';
import { useAuth } from '../auth/AuthContext';

// 동의가 없으면 서버가 일기 저장을 거부하므로(403), 첫 로그인 때 여기서 먼저 받는다.
export default function ConsentPage() {
  const { user, setConsent, logout } = useAuth();
  const [storage, setStorage] = useState(false);
  const [ai, setAi] = useState(false);
  const [research, setResearch] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const start = async () => {
    setBusy(true); setError('');
    try {
      await setConsent('diary_storage', true);
      if (ai) await setConsent('ai_counseling', true);
      if (research) await setConsent('ai_training', true);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth">
      <h1>시작하기 전에</h1>
      <p className="muted">{user?.nickname}님, 아래 내용을 확인하고 동의해 주세요. 동의는 언제든 설정에서 바꿀 수 있어요.</p>

      <label className="check card">
        <input type="checkbox" checked={storage} onChange={(e) => setStorage(e.target.checked)} />
        <span><b>[필수] 일기와 컨디션 기록 저장</b><br />
          <span className="muted small">일기 본문은 암호화해서 저장돼요. 내 데이터는 설정에서 내려받거나 삭제할 수 있어요.</span></span>
      </label>

      <label className="check card">
        <input type="checkbox" checked={ai} onChange={(e) => setAi(e.target.checked)} />
        <span><b>[선택] AI 감정 추천</b><br />
          <span className="muted small">추천을 누를 때만 그 일기 내용이 외부 AI 서비스로 전송돼요. 동의하지 않아도 모든 기능을 쓸 수 있어요.</span></span>
      </label>

      <label className="check card">
        <input type="checkbox" checked={research} onChange={(e) => setResearch(e.target.checked)} />
        <span><b>[선택] 연구 활용</b><br />
          <span className="muted small">일기를 쓸 때 "이 일기를 연구에 써도 돼요"를 직접 체크한 일기만, 이름·아이디 같은 정보를 뺀 채 연구에 쓰여요.
            체크하지 않은 일기는 쓰이지 않아요. 설정에서 언제든 끌 수 있고, 끄면 모든 일기가 연구에서 빠져요.
            다만 이미 익명으로 분석에 들어간 자료는 되돌리기 어려울 수 있어요. 동의하지 않아도 모든 기능을 쓸 수 있어요.</span></span>
      </label>

      <p className="muted small">MoodNote는 기록을 돕는 앱이고, 의료 서비스나 진단 도구가 아니에요.</p>

      {error && <p className="msg error" role="alert">{error}</p>}
      <button className="btn primary full" disabled={!storage || busy} onClick={start}>{busy ? '잠시만요…' : '동의하고 시작하기'}</button>
      <button className="btn ghost full" onClick={logout}>로그아웃</button>
    </main>
  );
}
