import React, { useEffect, useState } from 'react';
import { useMoodWords } from '../lib/useMoodWords';
import { ZONES, ZONE_ORDER } from '../lib/zones';
import Ball from './Ball';
import { MAX_MOODS } from '../lib/mood';

// 100단어를 4구역(25단어씩)으로 나눠 고르는 창.  구슬(색) → 구역 → 단어 순서.
// 단어와 구역은 서버의 mood_words 를 그대로 쓴다. (프론트에 목록을 따로 적어 두면 서버와 어긋날 수 있다)
// 감정은 최대 3개까지 고를 수 있다. 누르면 켜지고 다시 누르면 꺼진다. selectedIds: 고른 단어 id 목록, onToggle: 단어 하나를 켜고 끈다.
export default function MoodSelectorModal({ isOpen, onClose, onToggle, selectedIds = [] }) {
  const { words, byId, duplicates, error } = useMoodWords();
  const [zone, setZone] = useState('yellow');

  useEffect(() => {
    if (isOpen && selectedIds[0] && byId[selectedIds[0]]) setZone(byId[selectedIds[0]].zone);
    // 창을 열 때만 첫 번째로 고른 감정의 구역으로 맞춘다. (고를 때마다 구역이 바뀌면 불편하다)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, byId]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;
  const list = words.filter((w) => w.zone === zone);
  const full = selectedIds.length >= MAX_MOODS;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="감정 단어 고르기" onClick={(e) => e.stopPropagation()}>
        <h3>지금 마음은 어느 쪽에 가까워요?</h3>
        <p className="muted small">1) 에너지가 높은지 낮은지, 2) 기분이 좋은지 불쾌한지로 색을 먼저 고른 뒤 단어를 골라요. <b>최대 {MAX_MOODS}개</b>까지 고를 수 있고, 다른 색에서도 이어서 고를 수 있어요.</p>

        <div className="zone-grid">
          {ZONE_ORDER.map((z) => (
            <button
              key={z} type="button" data-zone={z} aria-pressed={zone === z}
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
          {list.map((w) => {
            const on = selectedIds.includes(w.id);
            return (
            <button
              key={w.id} type="button" data-zone={zone} aria-pressed={on} disabled={!on && full}
              className={`word-btn ${on ? 'selected' : ''}`}
              style={{ '--zone': ZONES[zone].color, '--zone-soft': ZONES[zone].soft }}
              onClick={() => onToggle({ id: w.id, word_ko: w.word_ko, zone: w.zone })}
            >
              <Ball id={w.id} size={40} className="word-ball" />
              <span className="word-text">{w.word_ko}{duplicates.has(w.word_ko) && <small> ({w.word_en})</small>}</span>
            </button>
            );
          })}
        </div>

        <button type="button" className="btn primary full" onClick={onClose}>
          {selectedIds.length ? `완료 (${selectedIds.length}/${MAX_MOODS})` : '닫기'}
        </button>
      </div>
    </div>
  );
}
