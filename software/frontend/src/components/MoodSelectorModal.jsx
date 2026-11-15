import React, { useEffect, useState } from 'react';
import { useMoodWords } from '../lib/useMoodWords';
import { ZONES, ZONE_ORDER } from '../lib/zones';

// 100단어를 4구역(25단어씩)으로 나눠 고르는 창.  구슬(색) → 구역 → 단어 순서.
// 단어와 구역은 서버의 mood_words 를 그대로 쓴다. (프론트에 목록을 따로 적어 두면 서버와 어긋날 수 있다)
export default function MoodSelectorModal({ isOpen, onClose, onSelect, selectedId }) {
  const { words, byId, duplicates, error } = useMoodWords();
  const [zone, setZone] = useState('yellow');

  useEffect(() => {
    if (isOpen && selectedId && byId[selectedId]) setZone(byId[selectedId].zone);
  }, [isOpen, selectedId, byId]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;
  const list = words.filter((w) => w.zone === zone);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="감정 단어 고르기" onClick={(e) => e.stopPropagation()}>
        <h3>지금 마음은 어느 쪽에 가까워요?</h3>
        <p className="muted small">1) 에너지가 높은지 낮은지, 2) 기분이 좋은지 불쾌한지로 색을 먼저 고른 뒤 단어를 골라요.</p>

        <div className="zone-grid">
          {ZONE_ORDER.map((z) => (
            <button
              key={z} type="button"
              className={`zone-btn ${zone === z ? 'active' : ''}`}
              style={{ '--zone': ZONES[z].color, '--zone-soft': ZONES[z].soft }}
              onClick={() => setZone(z)}
            >
              <b>{ZONES[z].label}</b>
              <span>{ZONES[z].desc}</span>
            </button>
          ))}
        </div>

        {error && <p className="msg error">{error}</p>}
        {!error && !words.length && <p className="muted">단어를 불러오는 중…</p>}

        <div className="word-grid">
          {list.map((w) => (
            <button
              key={w.id} type="button"
              className={`word-btn ${w.id === selectedId ? 'selected' : ''}`}
              style={{ '--zone': ZONES[zone].color, '--zone-soft': ZONES[zone].soft }}
              onClick={() => { onSelect({ id: w.id, word_ko: w.word_ko, zone: w.zone }); onClose(); }}
            >
              {w.word_ko}{duplicates.has(w.word_ko) && <small> ({w.word_en})</small>}
            </button>
          ))}
        </div>

        <button type="button" className="btn ghost full" onClick={onClose}>닫기</button>
      </div>
    </div>
  );
}
