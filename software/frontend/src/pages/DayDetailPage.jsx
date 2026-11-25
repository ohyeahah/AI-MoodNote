import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import Art from '../components/Art';
import Ball from '../components/Ball';
import MoodSelectorModal from '../components/MoodSelectorModal';
import ResearchToggle from '../components/ResearchToggle';
import { formatKo } from '../lib/dates';
import { MAX_MOODS } from '../lib/mood';

// ② 하루 상세. 그날의 일기(여러 개일 수 있음)와 컨디션. 일기는 수정·삭제할 수 있다.
const COND_ROWS = [
  ['sleep_hours', '수면', '시간', 'cond-sleep-hours'], ['sleep_score', '수면의 질', '/5', 'cond-sleep-quality'], ['meal_count', '끼니', '끼', 'cond-meal'],
  ['appetite_score', '식욕', '/5', 'cond-appetite'], ['bowel_score', '배변', '/5', 'cond-bowel'], ['exercise_minutes', '운동', '분', 'cond-exercise'],
  ['caffeine_cups', '카페인', '잔', 'cond-caffeine'], ['water_cups', '물', '잔', 'cond-water'],
];

function DiaryCard({ diary, onChanged }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(diary.content);
  const toMoods = (d) => (d.mood_words || []).map((w) => ({ id: w.id, word_ko: w.word_ko, zone: w.zone }));
  const [moods, setMoods] = useState(toMoods(diary));
  const [modal, setModal] = useState(false);
  const [error, setError] = useState('');
  const { consents } = useAuth();
  const researchConsent = !!consents?.ai_training?.granted;
  const [research, setResearch] = useState(!!diary.research_use);

  const save = async () => {
    setError('');
    try {
      await apiRequest(`/api/diaries/${diary.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ content: text, ...(moods.length ? { mood_word_ids: moods.map((m) => m.id) } : {}), ...(researchConsent ? { research_use: research } : {}) }),
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
      <p className="diary-mood">
        {(editing ? moods : (diary.mood ? [diary.mood] : [])).map((m) => <Ball key={m.id} id={m.id} size={40} />)}
        <b>{editing ? (moods.map((m) => m.word_ko).join(' · ') || '감정 없음') : (diary.mood_words?.map((m) => m.word_ko).join(' · ') || '감정 없음')}</b>
        {editing && <button type="button" className="link" onClick={() => setModal(true)}>바꾸기</button>}
      </p>
      {editing ? (
        <>
          <textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} />
          {researchConsent && <ResearchToggle checked={research} onChange={setResearch} />}
          <div className="row">
            <button type="button" className="btn primary" onClick={save} disabled={!text.trim()}>저장</button>
            <button type="button" className="btn ghost" onClick={() => { setEditing(false); setText(diary.content); setMoods(toMoods(diary)); setResearch(!!diary.research_use); }}>취소</button>
          </div>
        </>
      ) : (
        <>
          <p className="diary-text">{diary.content}</p>
          {diary.research_use && <p className="muted small">연구에 써도 되는 일기로 표시돼 있어요.</p>}
          <div className="row">
            <button type="button" className="btn ghost" onClick={() => setEditing(true)}>수정</button>
            <button type="button" className="btn ghost danger" onClick={remove}>삭제</button>
          </div>
        </>
      )}
      {error && <p className="msg error" role="alert">{error}</p>}
      <MoodSelectorModal isOpen={modal} onClose={() => setModal(false)} selectedIds={moods.map((m) => m.id)}
        onToggle={(m) => setMoods((prev) => (prev.some((x) => x.id === m.id) ? prev.filter((x) => x.id !== m.id) : prev.length >= MAX_MOODS ? prev : [...prev, m]))} />
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
        <button type="button" className="art-btn" aria-label="달력으로" onClick={() => navigate('/calendar')}><Art name="icon-back" size={32} /></button>
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
            {shown.map(([k, label, unit, icon]) => <div key={k}><dt><Art name={icon} size={22} />{label}</dt><dd>{cond[k]}{unit}</dd></div>)}
          </dl>
        ) : <p className="muted">기록한 컨디션이 없어요.</p>}
      </section>
    </div>
  );
}
