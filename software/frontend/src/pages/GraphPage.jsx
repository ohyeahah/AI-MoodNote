import React, { useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../api/client';
import Art, { artSrc } from '../components/Art';
import { WEEKDAYS, addDays, daysBetween, formatKo, todayKST } from '../lib/dates';
import { ZONES, ZONE_ORDER } from '../lib/zones';

// ③ 감정 그래프. Energy(에너지)와 Pleasant(기분)를 1~10 점수로 두 선으로 그린다.
// 디자이너의 격자 그림이 오면 아래 <rect> 격자를 <image> 로 바꾸면 된다.
const W = 340, H = 240, L = 48, R = 18, T = 18, B = 40;
// 한 번에 일주일씩 보여 준다. 시작 요일과 끝 요일이 같다. (예: 수요일 ~ 다음 수요일 = 8일)
// 7일만 보고 싶으면 SPAN 을 7 로 바꾸면 된다.
const SPAN = 8;
const weekdayOf = (s) => WEEKDAYS[new Date(`${s}T00:00:00Z`).getUTCDay()];
const shortDate = (s) => `${Number(s.slice(5, 7))}/${Number(s.slice(8))}(${weekdayOf(s)})`;
const COLORS = { energy: '#E8605A', pleasant: '#4A86E8' };      // 점 그림(R1 분홍빛 빨강, R2 파랑)과 선 색을 맞춘다
const COND_LABELS = { sleep_hours: '수면', meal_count: '끼니', exercise_minutes: '운동(분)', caffeine_cups: '카페인', water_cups: '물' };

export default function GraphPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [picked, setPicked] = useState(null);       // 눌러서 고른 날의 date

  const today = todayKST();
  const [to, setTo] = useState(today);              // 보고 있는 주의 마지막 날
  const from = addDays(to, -(SPAN - 1));
  const canNext = to < today;
  const moveWeek = (dir) => setTo((t) => { const n = addDays(t, dir * 7); return n > today ? today : n; });

  useEffect(() => {
    setPicked(null);
    apiRequest(`/api/mood/graph?from=${from}&to=${to}`)
      .then((d) => { setData(d); setError(''); })
      .catch((e) => { setData(null); setError(e.message); });
  }, [from, to]);

  const x = (date) => L + (daysBetween(from, date) / (SPAN - 1)) * (W - L - R);
  const y = (v) => T + ((10 - v) / 9) * (H - T - B);       // 점수 10 이 맨 위, 1 이 맨 아래

  const points = useMemo(() => (data?.days || []).filter((d) => d.avg_energy !== null), [data]);
  const line = (key) => points.map((d, i) => `${i ? 'L' : 'M'}${x(d.date).toFixed(1)} ${y(d[key]).toFixed(1)}`).join(' ');
  const day = points.find((d) => d.date === picked);
  const dot = 18;
  const ring = dot + 12;
  const ticks = Array.from({ length: SPAN }, (_, i) => addDays(from, i));

  return (
    <div className="page">
      <h2>감정 그래프</h2>
      <div className="row between">
        <button type="button" className="art-btn" aria-label="이전 주" onClick={() => moveWeek(-1)}><Art name="icon-back" size={32} /></button>
        <h3 className="week-title">{shortDate(from)} ~ {shortDate(to)}</h3>
        <button type="button" className="art-btn" aria-label="다음 주" disabled={!canNext} onClick={() => moveWeek(1)}><Art name="icon-next" size={32} /></button>
      </div>

      {error && <p className="msg error" role="alert">{error}</p>}

      <section className="card">
        <ul className="legend inline">
          <li><Art name="dot-energy" size={18} />에너지</li>
          <li><Art name="dot-mood" size={18} />기분(Pleasant)</li>
        </ul>

        <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="에너지와 기분 점수의 변화">
          {[2, 4, 6, 8, 10].map((v) => (
            <g key={v}>
              <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="var(--line)" />
              <text x={L - 14} y={y(v) + 4} textAnchor="end" className="axis">{v}</text>
            </g>
          ))}
          <line x1={L} x2={W - R} y1={y(5.5)} y2={y(5.5)} stroke="var(--muted)" strokeDasharray="4 4" />
          {ticks.map((t) => (
            <g key={t}>
              <text x={x(t)} y={H - 22} textAnchor="middle" className="axis">{weekdayOf(t)}</text>
              <text x={x(t)} y={H - 8} textAnchor="middle" className="axis">{Number(t.slice(8))}</text>
            </g>
          ))}

          <path d={line('avg_energy')} fill="none" stroke={COLORS.energy} strokeWidth="2.5" strokeLinejoin="round" />
          <path d={line('avg_pleasantness')} fill="none" stroke={COLORS.pleasant} strokeWidth="2.5" strokeLinejoin="round" />
          {points.map((d) => (
            <g key={d.date} onClick={() => setPicked(d.date)} className="pt">
              {d.date === picked && (
                <>
                  <image href={artSrc('dot-ring')} x={x(d.date) - ring / 2} y={y(d.avg_energy) - ring / 2} width={ring} height={ring} />
                  <image href={artSrc('dot-ring')} x={x(d.date) - ring / 2} y={y(d.avg_pleasantness) - ring / 2} width={ring} height={ring} />
                </>
              )}
              <image href={artSrc('dot-energy')} x={x(d.date) - dot / 2} y={y(d.avg_energy) - dot / 2} width={dot} height={dot} />
              <image href={artSrc('dot-mood')} x={x(d.date) - dot / 2} y={y(d.avg_pleasantness) - dot / 2} width={dot} height={dot} />
              <rect x={x(d.date) - 12} y={T} width="24" height={H - T - B} fill="transparent" />
            </g>
          ))}
        </svg>
        <p className="muted small">점을 누르면 그날의 감정 단어를 볼 수 있어요. 점선은 중간(5.5)이에요.</p>
        {data && !points.length && (
          <div className="empty-state">
            <img src={artSrc('empty')} width="120" height="80" alt="" aria-hidden="true" draggable="false" />
            <p className="muted">이 기간에 기록이 없어요.</p>
          </div>
        )}
      </section>

      {day && (
        <section className="card">
          <h3>{formatKo(day.date)}</h3>
          <p>{day.entries.map((e) => e.word_ko).join(', ')}</p>
          <p className="muted small">에너지 {day.avg_energy} · 기분 {day.avg_pleasantness}</p>
          {day.condition && (
            <p className="muted small">
              {Object.entries(COND_LABELS).filter(([k]) => day.condition[k] != null).map(([k, l]) => `${l} ${day.condition[k]}`).join(' · ')}
            </p>
          )}
        </section>
      )}

      {data && (
        <section className="card">
          <h3>구역별 기록 수</h3>
          <ul className="legend inline">
            {ZONE_ORDER.map((z) => <li key={z}><span className="dot" style={{ background: ZONES[z].color }} />{ZONES[z].label} {data.zone_counts[z]}</li>)}
          </ul>
        </section>
      )}
    </div>
  );
}
