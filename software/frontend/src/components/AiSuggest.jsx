import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { zoneColor } from '../lib/zones';

// 일기를 쓴 뒤 "AI 추천받기"를 누르면 후보 단어 3개가 나오고, 누르면 위의 감정 칸이 채워진다.
// 추천은 참고용이다. 어떤 단어를 추천했는지도 같이 저장해서(onSuggested), 나중에 학습 데이터에서 추천에 끌린 기록을 구분한다.
export default function AiSuggest({ content, aiConsent, onPick, onSuggested, onOpenModal }) {
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [error, setError] = useState('');

  const fetchSuggest = async () => {
    setLoading(true); setError('');
    try {
      const data = await apiRequest('/api/ai/mood-suggest', { method: 'POST', body: JSON.stringify({ content }) });
      setSuggestions(data.suggestions);
      onSuggested(data.suggestions.map((s) => s.id));
    } catch (e) {
      setSuggestions([]);
      setError(e.message || '지금은 추천을 못 받아요. 직접 감정을 선택해 주세요.');
    } finally {
      setLoading(false);
    }
  };

  const disabled = loading || !aiConsent || !content.trim();

  return (
    <section className="card">
      <button type="button" className="btn secondary full" disabled={disabled} onClick={fetchSuggest}>
        {loading ? 'AI가 읽고 있어요…' : '✨ AI 감정 추천받기'}
      </button>

      {!aiConsent && (
        <p className="muted small">AI 추천은 일기를 외부 AI 서비스로 보내야 해서 동의가 필요해요. <Link to="/settings">설정에서 켜기</Link></p>
      )}
      {aiConsent && !content.trim() && <p className="muted small">일기를 먼저 적으면 추천받을 수 있어요.</p>}

      {error && (
        <p className="msg error">{error} <button type="button" className="link" onClick={onOpenModal}>직접 고르기</button></p>
      )}

      {suggestions.length > 0 && (
        <div className="suggestions">
          <p className="muted small">누르면 위의 감정 칸에 들어가요. 최종 선택은 내가 해요.</p>
          {suggestions.map((s) => (
            <button key={s.id} type="button" className="suggest" onClick={() => onPick({ id: s.id, word_ko: s.word_ko, zone: s.zone })}>
              <span className="dot" style={{ background: zoneColor(s.zone) }} />
              <b>{s.word_ko}</b>
              {s.reason && <span className="muted small">{s.reason}</span>}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
