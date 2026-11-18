import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../api/client';
import Art from '../components/Art';
import Ball from '../components/Ball';
import Scale from '../components/Scale';

// 설정 > 의견 보내기. 종류를 고르고, 만족도(선택)와 내용을 적어서 보낸다.
// 의견은 일기와 달리 암호화되지 않고 개발팀이 읽는다. 그래서 일기 내용은 적지 않도록 안내한다.
const CATEGORIES = [
  { id: 'bug', label: '불편한 점', placeholder: '어느 화면에서 무엇이 잘 안 됐나요? 자세히 적어 주면 고치기 쉬워요.' },
  { id: 'idea', label: '바라는 점', placeholder: '이런 기능이나 화면이 있으면 좋겠어요.' },
  { id: 'praise', label: '좋은 점', placeholder: '마음에 들었던 점을 알려 주세요.' },
  { id: 'other', label: '기타', placeholder: '하고 싶은 말을 편하게 적어 주세요.' },
];
const MIN = 5;
const MAX = 1000;
const THANKS_BALL = 17;   // 쾌활한 (노란 공)

export default function FeedbackPage() {
  const navigate = useNavigate();
  const [category, setCategory] = useState('idea');
  const [rating, setRating] = useState(null);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [sent, setSent] = useState(false);

  const current = CATEGORIES.find((c) => c.id === category);
  const length = message.trim().length;
  const canSend = length >= MIN && !sending;

  const send = async () => {
    setError(null);
    setSending(true);
    try {
      await apiRequest('/api/feedback', { method: 'POST', body: JSON.stringify({ category, rating, message }) });
      setSent(true);
    } catch (e) {
      setError(e.message);   // 실패하면 쓴 글은 그대로 두어서 다시 보낼 수 있다
    } finally {
      setSending(false);
    }
  };

  const again = () => { setMessage(''); setRating(null); setCategory('idea'); setSent(false); };

  return (
    <div className="page">
      <div className="row between">
        <button type="button" className="art-btn" aria-label="설정으로" onClick={() => navigate('/settings')}><Art name="icon-back" size={32} /></button>
        <h2>의견 보내기</h2>
        <span />
      </div>

      {sent ? (
        <section className="card fb-thanks" role="status">
          <Ball id={THANKS_BALL} size={72} />
          <h3>고마워요, 잘 받았어요!</h3>
          <p className="muted small">보내 준 의견은 MoodNote를 고치는 데 쓸게요.</p>
          <button type="button" className="btn primary full" onClick={() => navigate('/settings')}>설정으로 돌아가기</button>
          <button type="button" className="btn ghost full" onClick={again}>의견 하나 더 보내기</button>
        </section>
      ) : (
        <>
          <p className="muted">불편한 점이든 바라는 점이든 좋아요. 하나하나 읽고 있어요.</p>
          {error && <p className="msg error" role="alert">{error}</p>}

          <section className="card stack">
            <span className="field-label">어떤 의견인가요?</span>
            <div className="seg" role="group" aria-label="의견 종류">
              {CATEGORIES.map((c) => (
                <button key={c.id} type="button" className={category === c.id ? 'on' : ''} aria-pressed={category === c.id}
                  onClick={() => setCategory(c.id)}>{c.label}</button>
              ))}
            </div>

            <Scale label="MoodNote, 어때요? (선택)" low="별로예요" high="좋아요" value={rating} onChange={setRating} />

            <label>
              <span className="field-label">내용</span>
              <textarea rows={6} maxLength={MAX} value={message} placeholder={current.placeholder}
                onChange={(e) => setMessage(e.target.value)} />
            </label>
            <span className={`small counter ${length > 0 && length < MIN ? 'short' : 'muted'}`}>
              {length > 0 && length < MIN ? `${MIN}자 이상 적어 주세요 · ` : ''}{length}/{MAX}
            </span>
          </section>

          <p className="help small">
            의견은 일기처럼 암호화되지 않고 개발팀이 읽어요. <strong>일기 내용이나 개인 정보는 적지 말아 주세요.</strong>
            {' '}탈퇴하면 보낸 의견도 함께 지워져요.
          </p>

          <button type="button" className="btn primary full" disabled={!canSend} onClick={send}>
            {sending ? '보내는 중…' : '보내기'}
          </button>
        </>
      )}
    </div>
  );
}
