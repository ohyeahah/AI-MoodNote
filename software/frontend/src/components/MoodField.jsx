import React, { useState } from 'react';
import { ZONES, ZONE_ORDER, zoneColor } from '../lib/zones';

// 일기 칸 바로 위의 "오늘의 감정" 칸. 무드미터를 처음 보는 사람을 위해 ? 도움말이 있다.
export default function MoodField({ mood, onOpen }) {
  const [help, setHelp] = useState(false);
  return (
    <section className="card">
      <div className="row between">
        <h3>오늘의 감정</h3>
        <button type="button" className="icon-btn" aria-expanded={help} aria-label="무드미터 도움말" onClick={() => setHelp(!help)}>?</button>
      </div>

      <button type="button" className="mood-chip" onClick={onOpen}>
        {mood ? (
          <>
            <span className="dot" style={{ background: zoneColor(mood.zone) }} />
            {mood.word_ko}
            <span className="muted small">· 바꾸기</span>
          </>
        ) : (
          <span className="muted">감정 단어 고르기</span>
        )}
      </button>

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
