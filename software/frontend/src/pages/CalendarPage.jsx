import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { WEEKDAYS, addDays, daysInMonth, firstWeekday, formatKo, todayKST, ymd } from '../lib/dates';
import { buildMonthComment, buildWeekComment } from '../lib/comment';
import Art from '../components/Art';
import Ball from '../components/Ball';
import { ZONES, ZONE_ORDER } from '../lib/zones';

// ④ 달력. 기록이 있는 날은 그날 마지막 기록의 구역 색 구슬을 보여 준다.
// 연·월은 가운데 드롭다운으로 바로 고를 수 있다.
// 날짜를 누르면 '선택'되고, 코멘트가 그날까지 최근 7일 기준으로 바뀐다. (다시 누르면 선택이 풀리고 월 기준으로 돌아간다)
// 선택한 날의 일기는 코멘트 칸의 버튼으로 본다.
export default function CalendarPage() {
  const navigate = useNavigate();
  const today = todayKST();
  const thisYear = Number(today.slice(0, 4));
  const [year, setYear] = useState(thisYear);
  const [month, setMonth] = useState(Number(today.slice(5, 7)));
  const [selected, setSelected] = useState(null);
  const [dayMap, setDayMap] = useState({});     // 날짜 → 그날 기록(서버 days 항목). 지난달 1일부터 이번 달 끝까지 한 번에 받는다
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // 지난달부터 받는 이유: 코멘트가 지난달(또는 그 전 7일)과 비교하기 때문이다. 어느 날을 골라도 13일 전까지는 지난달 안에 들어온다.
    const prev = new Date(year, month - 2, 1);
    const from = ymd(prev.getFullYear(), prev.getMonth() + 1, 1);
    const to = ymd(year, month, daysInMonth(year, month));
    let alive = true;                            // 연·월을 빠르게 바꿨을 때 늦게 도착한 옛 응답을 버린다
    setLoaded(false);
    apiRequest(`/api/mood/graph?from=${from}&to=${to}`)
      .then((data) => {
        if (!alive) return;
        const map = {};
        data.days.forEach((d) => { map[d.date] = d; });
        setDayMap(map); setError(''); setLoaded(true);
      })
      .catch((e) => { if (alive) { setDayMap({}); setError(e.message); setLoaded(true); } });
    return () => { alive = false; };
  }, [year, month]);

  useEffect(() => { setSelected(null); }, [year, month]);   // 달을 바꾸면 선택을 푼다

  const move = (delta) => {
    const dt = new Date(year, month - 1 + delta, 1);
    setYear(dt.getFullYear()); setMonth(dt.getMonth() + 1);
  };
  const goToday = () => { setYear(thisYear); setMonth(Number(today.slice(5, 7))); };
  const isThisMonth = year === thisYear && month === Number(today.slice(5, 7));

  const comment = useMemo(() => {
    if (!loaded || error) return null;
    const between = (a, b) => Object.values(dayMap).filter((d) => d.date >= a && d.date <= b);
    if (selected) {
      return buildWeekComment({
        label: `${formatKo(selected)}까지 최근 7일`,
        days: between(addDays(selected, -6), selected),
        prevDays: between(addDays(selected, -13), addDays(selected, -7)),
      });
    }
    const first = ymd(year, month, 1);
    const last = ymd(year, month, daysInMonth(year, month));
    const prev = new Date(year, month - 2, 1);
    const elapsed = today < first ? 0 : today >= last ? daysInMonth(year, month) : Number(today.slice(8, 10));
    return buildMonthComment({
      label: `${year}년 ${month}월`, elapsedDays: elapsed,
      days: between(first, last),
      prevDays: between(ymd(prev.getFullYear(), prev.getMonth() + 1, 1), addDays(first, -1)),
    });
  }, [loaded, error, dayMap, selected, year, month, today]);

  const blanks = Array.from({ length: firstWeekday(year, month) });
  const days = Array.from({ length: daysInMonth(year, month) }, (_, i) => i + 1);
  const lastMood = (date) => { const es = dayMap[date]?.entries; return es && es.length ? es[es.length - 1] : null; };   // 그날 마지막 기록
  const years = Array.from({ length: Math.max(thisYear + 1, year) - Math.min(thisYear - 5, year) + 1 }, (_, i) => Math.min(thisYear - 5, year) + i);

  return (
    <div className="page">
      <div className="ym">
        <button type="button" className="art-btn" aria-label="이전 달" onClick={() => move(-1)}><Art name="icon-back" size={32} /></button>
        <div className="ym-pick">
          <select aria-label="연도" value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {years.map((y) => <option key={y} value={y}>{y}년</option>)}
          </select>
          <select aria-label="월" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => <option key={m} value={m}>{m}월</option>)}
          </select>
        </div>
        <button type="button" className="art-btn" aria-label="다음 달" onClick={() => move(1)}><Art name="icon-next" size={32} /></button>
      </div>

      <div className="row between">
        <ul className="legend inline">
          {ZONE_ORDER.map((z) => <li key={z}><span className="dot" style={{ background: ZONES[z].color }} />{ZONES[z].label}</li>)}
        </ul>
        {!isThisMonth && <button type="button" className="link" onClick={goToday}>이번 달로</button>}
      </div>

      {error && <p className="msg error">{error}</p>}

      <div className="cal">
        {WEEKDAYS.map((w) => <div key={w} className="cal-head">{w}</div>)}
        {blanks.map((_, i) => <div key={`b${i}`} />)}
        {days.map((d) => {
          const date = ymd(year, month, d);
          const mood = lastMood(date);
          return (
            <button key={d} type="button" aria-pressed={date === selected}
              className={`cal-day ${date === today ? 'today' : ''} ${date === selected ? 'selected' : ''}`}
              onClick={() => setSelected((s) => (s === date ? null : date))}>
              <span className="cal-num">{d}</span>
              {mood && (
                <span className="cal-ball" role="img" aria-label={`${mood.word_ko} (${ZONES[mood.zone].label})`}>
                  <Ball id={mood.mood_word_id} size={32} />
                </span>
              )}
            </button>
          );
        })}
      </div>

      <section className="card comment" aria-live="polite">
        <h3>코멘트</h3>
        {comment ? (
          <>
            <p className="muted small">{comment.basis}</p>
            <ul className="comment-list">
              {comment.lines.map((line, i) => <li key={i}>{line}</li>)}
            </ul>
          </>
        ) : <p className="muted small">{error ? '기록을 불러오지 못해서 코멘트를 만들 수 없어요.' : '불러오는 중…'}</p>}
        {selected ? (
          <>
            <button type="button" className="btn ghost full" onClick={() => navigate(`/detail/${selected}`)}>{formatKo(selected)} 일기 보기</button>
            <button type="button" className="link" onClick={() => setSelected(null)}>선택 풀고 {month}월 전체 보기</button>
          </>
        ) : <p className="muted small">날짜를 누르면 그날까지 최근 7일을 보고 코멘트를 달아 줘요.</p>}
      </section>
    </div>
  );
}
