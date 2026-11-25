import React from 'react';

// 일기마다 '연구에 써도 돼요'를 고르는 칸. 연구 활용에 동의한 사람에게만 보여 주고, 기본은 꺼짐이다.
export default function ResearchToggle({ checked, onChange }) {
  return (
    <label className="check research-toggle">
      <input type="checkbox" checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
      <span>이 일기를 연구에 써도 돼요
        <span className="muted small"> · 체크하지 않은 일기는 연구에 쓰이지 않아요</span></span>
    </label>
  );
}
