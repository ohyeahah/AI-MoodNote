import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { WEEKDAYS, daysInMonth, firstWeekday, todayKST, ymd } from '../lib/dates';
import { ZONES, ZONE_ORDER, zoneColor } from '../lib/zones';

// ④ 달력. 기록이 있는 날은 그날 마지막 기록의 구역 색 구슬을 보여 주고, 날짜를 누르면 ② 하루 상세로 간다.
export default function CalendarPage() {
  const navigate = useNavigate();
  const today = todayKST();
  const [year, setYear] = useState(Number(today.slice(0, 4)));
  const [month, setMonth] = useState(Number(today.slice(5, 7)));
  const [zoneByDay, setZoneByDay] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    const from = ymd(year, month, 1);
    const to = ymd(year, month, daysInMonth(year, month));
    apiRequest(`/api/mood/graph?from=${from}&to=${to}`)
      .then((data) => {
        const map = {};
        data.days.forEach((d) => { if (d.entries.length) map[d.date] = d.entries[d.entries.length - 1].zone; });
        setZoneByDay(map); setError('');
      })
      .catch((e) => { setZoneByDay({}); setError(e.message); });
  }, [year, month]);

  const move = (delta) => {
    const dt = new Date(year, month - 1 + delta, 1);
    setYear(dt.getFullYear()); setMonth(dt.getMonth() + 1);
  };

  const blanks = Array.from({ length: firstWeekday(year, month) });
  const days = Array.from({ length: daysInMonth(year, month) }, (_, i) => i + 1);

  return (
    <div className="page">
      <div className="row between">
        <button type="button" className="icon-btn" aria-label="이전 달" onClick={() => move(-1)}>‹</button>
        <h2>{year}년 {month}월</h2>
        <button type="button" className="icon-btn" aria-label="다음 달" onClick={() => move(1)}>›</button>
      </div>

      <ul className="legend inline">
        {ZONE_ORDER.map((z) => <li key={z}><span className="dot" style={{ background: ZONES[z].color }} />{ZONES[z].label}</li>)}
      </ul>

      {error && <p className="msg error">{error}</p>}

      <div className="cal">
        {WEEKDAYS.map((w) => <div key={w} className="cal-head">{w}</div>)}
        {blanks.map((_, i) => <div key={`b${i}`} />)}
        {days.map((d) => {
          const date = ymd(year, month, d);
          const zone = zoneByDay[date];
          return (
            <button key={d} type="button" className={`cal-day ${date === today ? 'today' : ''}`} onClick={() => navigate(`/detail/${date}`)}>
              <span>{d}</span>
              {zone && <i className="ball" style={{ background: zoneColor(zone) }} aria-label={ZONES[zone].label} />}
            </button>
          );
        })}
      </div>

      <section className="card comment">
        <h3>코멘트</h3>
        <p className="muted small">나중에 패턴 분석 결과가 여기에 나와요.</p>
      </section>
    </div>
  );
}
