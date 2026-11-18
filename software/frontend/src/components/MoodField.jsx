import React, { useState } from 'react';
import { ZONES, ZONE_ORDER } from '../lib/zones';
import Art from './Art';
import Ball from './Ball';
import { MAX_MOODS, representative } from '../lib/mood';
import { useMoodWords } from '../lib/useMoodWords';

// 일기 칸 바로 위의 "오늘의 감정" 칸. 감정을 최대 3개 고르고, 평균에 가장 가까운 감정이 대표 공이 된다.
// 무드미터를 처음 보는 사람을 위해 ? 도움말이 있다.
export default function MoodField({ moods, onOpen, title = '오늘의 감정' }) {
  const [help, setHelp] = useState(false);
  const { byId } = useMoodWords();
  const rep = moods.length > 1 ? representative(moods, byId) : null;
  return (
    <section className="card">
      <div className="row between">
        <h3>{title} <span className="muted small">(최대 {MAX_MOODS}개)</span></h3>
        <button type="button" className="art-btn" aria-expanded={help} aria-label="무드미터 도움말" onClick={() => setHelp(!help)}><Art name="icon-help" size={32} /></button>
      </div>

      <button type="button" className={`mood-chip ${moods.length ? 'filled' : 'empty'}`} onClick={onOpen}>
        {moods.length ? (
          <>
            <span className="mood-picks">
              {moods.map((m) => (
                <span key={m.id} className="mood-pick"><Ball id={m.id} size={32} /><span className="mood-word">{m.word_ko}</span></span>
              ))}
            </span>
            <span className="muted small">· 바꾸기</span>
          </>
        ) : (
          <span className="muted">감정 단어 고르기</span>
        )}
      </button>

      {rep && (
        <p className="mood-result">
          <Ball id={rep.id} size={36} />
          <span><b>{rep.word_ko}</b> <span className="muted small">— 고른 감정들의 평균에 가장 가까워요. 달력과 그래프에는 이 공이 나와요.</span></span>
        </p>
      )}

      {help && (
        <div className="help">
          <p className="small">무드미터는 감정을 <b>에너지</b>(높음/낮음)와 <b>기분</b>(불쾌/유쾌) 두 가지로 나눠 100개 단어로 보여 줘요.</p>
          <ul className="legend">
            {ZONE_ORDER.map((z) => (
              <li key={z}><span className="dot" style={{ background: ZONES[z].color }} /><b>{ZONES[z].label}</b> {ZONES[z].desc}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
