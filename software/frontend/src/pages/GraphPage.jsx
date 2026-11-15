import React, { useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../api/client';
import { addDays, daysBetween, formatKo, todayKST } from '../lib/dates';
import { ZONES, ZONE_ORDER } from '../lib/zones';

// ③ 감정 그래프. Energy(에너지)와 Pleasant(기분)를 1~10 점수로 두 선으로 그린다.
// 디자이너의 격자 그림이 오면 아래 <rect> 격자를 <image> 로 바꾸면 된다.
const W = 340, H = 230, L = 30, R = 12, T = 14, B = 26;
const COLORS = { energy: '#E0743C', pleasant: '#3C8F6A' };
const COND_LABELS = { sleep_hours: '수면', meal_count: '끼니', exercise_minutes: '운동(분)', caffeine_cups: '카페인', water_cups: '물' };

export default function GraphPage() {
  const [period, setPeriod] = useState(7);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [picked, setPicked] = useState(null);       // 눌러서 고른 날의 date

  const to = todayKST();
  const from = addDays(to, -(period - 1));

  useEffect(() => {
    setPicked(null);
    apiRequest(`/api/mood/graph?from=${from}&to=${to}`)
      .then((d) => { setData(d); setError(''); })
      .catch((e) => { setData(null); setError(e.message); });
  }, [from, to]);

  const x = (date) => L + (daysBetween(from, date) / Math.max(period - 1, 1)) * (W - L - R);
  const y = (v) => T + ((10 - v) / 9) * (H - T - B);       // 점수 10 이 맨 위, 1 이 맨 아래

  const points = useMemo(() => (data?.days || []).filter((d) => d.avg_energy !== null), [data]);
  const line = (key) => points.map((d, i) => `${i ? 'L' : 'M'}${x(d.date).toFixed(1)} ${y(d[key]).toFixed(1)}`).join(' ');
  const day = points.find((d) => d.date === picked);
  const ticks = period === 7 ? Array.from({ length: 7 }, (_, i) => addDays(from, i)) : [0, 5, 10, 15, 20, 25, 29].map((i) => addDays(from, i));

  return (
    <div className="page">
      <h2>감정 그래프</h2>
      <div className="seg">
        {[7, 30].map((n) => <button key={n} type="button" className={period === n ? 'on' : ''} onClick={() => setPeriod(n)}>최근 {n}일</button>)}
      </div>

      {error && <p className="msg error" role="alert">{error}</p>}

      <section className="card">
        <ul className="legend inline">
          <li><span className="dot" style={{ background: COLORS.energy }} />에너지</li>
          <li><span className="dot" style={{ background: COLORS.pleasant }} />기분(Pleasant)</li>
        </ul>

        <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="에너지와 기분 점수의 변화">
          {[2, 4, 6, 8, 10].map((v) => (
            <g key={v}>
              <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="var(--line)" />
              <text x={L - 6} y={y(v) + 4} textAnchor="end" className="axis">{v}</text>
            </g>
          ))}
          <line x1={L} x2={W - R} y1={y(5.5)} y2={y(5.5)} stroke="var(--muted)" strokeDasharray="4 4" />
          {ticks.map((t) => <text key={t} x={x(t)} y={H - 8} textAnchor="middle" className="axis">{Number(t.slice(8))}</text>)}

          <path d={line('avg_energy')} fill="none" stroke={COLORS.energy} strokeWidth="2.5" strokeLinejoin="round" />
          <path d={line('avg_pleasantness')} fill="none" stroke={COLORS.pleasant} strokeWidth="2.5" strokeLinejoin="round" />
          {points.map((d) => (
            <g key={d.date} onClick={() => setPicked(d.date)} className="pt">
              <circle cx={x(d.date)} cy={y(d.avg_energy)} r="4.5" fill={COLORS.energy} />
              <circle cx={x(d.date)} cy={y(d.avg_pleasantness)} r="4.5" fill={COLORS.pleasant} />
              <rect x={x(d.date) - 12} y={T} width="24" height={H - T - B} fill="transparent" />
            </g>
          ))}
        </svg>
        <p className="muted small">점을 누르면 그날의 감정 단어를 볼 수 있어요. 점선은 중간(5.5)이에요.</p>
        {data && !points.length && <p className="muted">이 기간에 기록이 없어요.</p>}
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
