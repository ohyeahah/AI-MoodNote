import React from 'react';
import Art from './Art';

// 1~5 점수 고르기. 다시 누르면 비워진다 (선택 입력이라서).
export default function Scale({ label, icon, low, high, value, onChange }) {
  return (
    <div className="scale">
      <span className="scale-label">{icon && <Art name={icon} size={24} />}{label}</span>
      <div className="scale-row" role="group" aria-label={label}>
        <span className="muted small">{low}</span>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n} type="button" aria-pressed={value === n}
            className={`scale-btn ${value === n ? 'on' : ''}`}
            onClick={() => onChange(value === n ? null : n)}
          >{n}</button>
        ))}
        <span className="muted small">{high}</span>
      </div>
    </div>
  );
}
