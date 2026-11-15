import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../api/client';
import MoodSelectorModal from '../components/MoodSelectorModal';
import { formatKo } from '../lib/dates';
import { zoneColor } from '../lib/zones';

// ② 하루 상세. 그날의 일기(여러 개일 수 있음)와 컨디션. 일기는 수정·삭제할 수 있다.
const COND_ROWS = [
  ['sleep_hours', '수면', '시간'], ['sleep_score', '수면의 질', '/5'], ['meal_count', '끼니', '끼'],
  ['appetite_score', '식욕', '/5'], ['bowel_score', '배변', '/5'], ['exercise_minutes', '운동', '분'],
  ['caffeine_cups', '카페인', '잔'], ['water_cups', '물', '잔'],
];

function DiaryCard({ diary, onChanged }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(diary.content);
  const [mood, setMood] = useState(diary.mood);
  const [modal, setModal] = useState(false);
  const [error, setError] = useState('');

  const save = async () => {
    setError('');
    try {
      await apiRequest(`/api/diaries/${diary.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ content: text, ...(mood ? { mood_word_id: mood.id } : {}) }),
      });
      setEditing(false); onChanged();
    } catch (e) { setError(e.message); }
  };

  const remove = async () => {
    if (!window.confirm('이 일기를 삭제할까요? 되돌릴 수 없어요.')) return;
    try { await apiRequest(`/api/diaries/${diary.id}`, { method: 'DELETE' }); onChanged(); }
    catch (e) { setError(e.message); }
  };

  return (
    <section className="card">
      <p>
        <span className="dot" style={{ background: zoneColor(mood?.zone) }} />
        <b>{mood?.word_ko || '감정 없음'}</b>
        {editing && <button type="button" className="link" onClick={() => setModal(true)}>바꾸기</button>}
      </p>
      {editing ? (
        <>
          <textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} />
          <div className="row">
            <button type="button" className="btn primary" onClick={save} disabled={!text.trim()}>저장</button>
            <button type="button" className="btn ghost" onClick={() => { setEditing(false); setText(diary.content); setMood(diary.mood); }}>취소</button>
          </div>
        </>
      ) : (
        <>
          <p className="diary-text">{diary.content}</p>
          <div className="row">
            <button type="button" className="btn ghost" onClick={() => setEditing(true)}>수정</button>
            <button type="button" className="btn ghost danger" onClick={remove}>삭제</button>
          </div>
        </>
      )}
      {error && <p className="msg error" role="alert">{error}</p>}
      <MoodSelectorModal isOpen={modal} onClose={() => setModal(false)} selectedId={mood?.id} onSelect={setMood} />
    </section>
  );
}

export default function DayDetailPage() {
  const { date } = useParams();
  const navigate = useNavigate();
  const [diaries, setDiaries] = useState(null);
  const [cond, setCond] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [d, c] = await Promise.all([
        apiRequest(`/api/diaries?date=${date}`),
        apiRequest(`/api/daily-conditions?from=${date}&to=${date}`),
      ]);
      setDiaries(d.diaries);
      setCond(c.conditions.find((r) => r.source === 'self') || c.conditions[0] || null);
      setError('');
    } catch (e) { setError(e.message); }
  }, [date]);

  useEffect(() => { load(); }, [load]);

  const shown = cond ? COND_ROWS.filter(([k]) => cond[k] !== null && cond[k] !== undefined) : [];

  return (
    <div className="page">
      <div className="row between">
        <button type="button" className="icon-btn" aria-label="달력으로" onClick={() => navigate('/calendar')}>‹</button>
        <h2>{formatKo(date)}</h2>
        <span />
      </div>
      {error && <p className="msg error" role="alert">{error}</p>}
      {diaries === null && !error && <p className="muted">불러오는 중…</p>}

      {diaries && (diaries.length
        ? diaries.map((d) => <DiaryCard key={`${d.id}-${d.updated_at}`} diary={d} onChanged={load} />)
        : <section className="card"><p className="muted">이 날 쓴 일기가 없어요.</p></section>)}

      <section className="card">
        <h3>컨디션</h3>
        {shown.length ? (
          <dl className="cond">
            {shown.map(([k, label, unit]) => <div key={k}><dt>{label}</dt><dd>{cond[k]}{unit}</dd></div>)}
          </dl>
        ) : <p className="muted">기록한 컨디션이 없어요.</p>}
      </section>
    </div>
  );
}
