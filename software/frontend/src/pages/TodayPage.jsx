import React, { useCallback, useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import AiSuggest from '../components/AiSuggest';
import MoodField from '../components/MoodField';
import Art from '../components/Art';
import MoodSelectorModal from '../components/MoodSelectorModal';
import Scale from '../components/Scale';
import { formatKo, todayKST } from '../lib/dates';
import { MAX_MOODS } from '../lib/mood';

// ⑤ 오늘 기록 (메인). 위에서부터: 오늘의 감정 → 일기 → AI 추천 → 컨디션 → 저장.
const EMPTY = { sleep_hours: '', sleep_score: null, meal_count: '', appetite_score: null, bowel_score: null, exercise_minutes: '', caffeine_cups: '', water_cups: '' };
const NUM_FIELDS = [
  ['sleep_hours', '수면 시간 (시간)', { step: 0.5, min: 0, max: 24 }, 'cond-sleep-hours'],
  ['meal_count', '끼니 수', { step: 1, min: 0, max: 10 }, 'cond-meal'],
  ['exercise_minutes', '운동 (분)', { step: 5, min: 0, max: 1440 }, 'cond-exercise'],
  ['caffeine_cups', '카페인 (잔)', { step: 1, min: 0, max: 20 }, 'cond-caffeine'],
  ['water_cups', '물 (잔)', { step: 1, min: 0, max: 30 }, 'cond-water'],
];

// 칸이 비어 있으면 서버에 보내지 않는다. (처음부터 7시간·3끼를 채워 두면 안 쓴 날도 값이 기록되기 때문이다)
function condToPayload(c) {
  const out = {};
  Object.entries(c).forEach(([k, v]) => { if (v !== '' && v !== null) out[k] = Number(v); });
  return out;
}

export default function TodayPage() {
  const { consents } = useAuth();
  const aiConsent = !!consents?.ai_counseling?.granted;
  const today = todayKST();
  const [date, setDate] = useState(today);          // 기록할 날짜 (기본은 오늘, 지난 날로 바꿀 수 있다)
  const isToday = date === today;

  const [content, setContent] = useState('');
  const [moods, setMoods] = useState([]);           // 고른 감정 [{ id, word_ko, zone }] (최대 3개)
  const [aiIds, setAiIds] = useState([]);           // 이번 일기에서 AI가 추천한 단어 id
  const [diaryId, setDiaryId] = useState(null);     // 있으면 수정, 없으면 새로 저장
  const [cond, setCond] = useState(EMPTY);
  const [modal, setModal] = useState(false);
  const [msg, setMsg] = useState(null);             // { type: 'ok' | 'error', text }
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    // 날짜를 바꿀 때마다 이전 날의 내용이 남지 않도록 먼저 비운다.
    setLoaded(false); setDiaryId(null); setContent(''); setMoods([]); setAiIds([]); setCond(EMPTY); setMsg(null);
    try {
      const [d, c] = await Promise.all([
        apiRequest(`/api/diaries?date=${date}`),
        apiRequest(`/api/daily-conditions?from=${date}&to=${date}`),
      ]);
      const latest = d.diaries[0];                  // 오늘 쓴 일기 중 가장 최근 것
      if (latest) {
        setDiaryId(latest.id); setContent(latest.content || '');
        setMoods((latest.mood_words || []).map((w) => ({ id: w.id, word_ko: w.word_ko, zone: w.zone })));
        setAiIds(latest.ai_suggested_word_ids || []);
      }
      const self = c.conditions.find((r) => r.source === 'self');
      if (self) {
        setCond(Object.fromEntries(Object.keys(EMPTY).map((k) => [k, self[k] ?? EMPTY[k]])));
      }
    } catch (e) {
      setMsg({ type: 'error', text: e.message });
    } finally {
      setLoaded(true);
    }
  }, [date]);

  useEffect(() => { load(); }, [load]);

  // 감정을 고르면 '감정을 선택해야 저장할 수 있어요' 같은 이전 안내를 지운다.
  // 감정은 최대 3개. 모달에서는 누를 때마다 켜고 끄고(toggleMood), AI 추천을 누르면 하나 더한다(addMood).
  const toggleMood = (m) => {
    setMsg(null);
    setMoods((prev) => (prev.some((x) => x.id === m.id) ? prev.filter((x) => x.id !== m.id) : prev.length >= MAX_MOODS ? prev : [...prev, m]));
  };
  const addMood = (m) => {
    if (moods.some((x) => x.id === m.id)) return;
    if (moods.length >= MAX_MOODS) { setMsg({ type: 'error', text: `감정은 최대 ${MAX_MOODS}개까지 고를 수 있어요. 감정 칸에서 하나를 빼고 다시 눌러 주세요.` }); return; }
    setMsg(null); setMoods((prev) => [...prev, m]);
  };
  const changeDate = (v) => { if (v && v <= today) setDate(v); };   // 미래 날짜는 서버가 막으므로 여기서도 막는다
  const startNew = () => { setDiaryId(null); setContent(''); setMoods([]); setAiIds([]); setMsg(null); };
  const setNum = (k) => (e) => setCond((p) => ({ ...p, [k]: e.target.value }));

  const save = async (e) => {
    e.preventDefault();
    setMsg(null);
    if (!moods.length) { setMsg({ type: 'error', text: '감정을 선택해야 저장할 수 있어요.' }); setModal(true); return; }
    if (!content.trim()) { setMsg({ type: 'error', text: '일기 내용을 적어 주세요.' }); return; }

    setSaving(true);
    try {
      const payload = condToPayload(cond);
      if (Object.keys(payload).length) {
        await apiRequest('/api/daily-conditions', { method: 'PUT', body: JSON.stringify({ log_date: date, ...payload }) });
      }
      const body = { content, mood_word_ids: moods.map((m) => m.id), ai_suggested_word_ids: aiIds };
      if (diaryId) {
        await apiRequest(`/api/diaries/${diaryId}`, { method: 'PATCH', body: JSON.stringify(body) });
      } else {
        const r = await apiRequest('/api/diaries', { method: 'POST', body: JSON.stringify({ ...body, entry_date: date }) });
        setDiaryId(r.diary_id);
      }
      setMsg({ type: 'ok', text: '저장했어요.' });
    } catch (err) {
      setMsg({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <h2>{isToday ? '오늘 기록' : '지난 날 기록'} <span className="muted small">{formatKo(date)}</span></h2>
      <div className="date-pick">
        <label>
          <span className="small muted">기록할 날짜</span>
          <input type="date" value={date} max={today} onChange={(e) => changeDate(e.target.value)} />
        </label>
        {!isToday && <button type="button" className="btn ghost" onClick={() => setDate(today)}>오늘로</button>}
      </div>
      {!loaded && <p className="muted">불러오는 중…</p>}

      <MoodField moods={moods} title={isToday ? '오늘의 감정' : '이날의 감정'} onOpen={() => setModal(true)} />

      <form onSubmit={save} className="stack">
        <section className="card">
          <h3>일기</h3>
          <textarea rows={6} value={content} onChange={(e) => setContent(e.target.value)} maxLength={20000} placeholder={isToday ? '오늘 마음에 남은 생각을 적어 보세요.' : '그날 마음에 남았던 생각을 적어 보세요.'} />
        </section>

        <AiSuggest
          content={content} aiConsent={aiConsent}
          onPick={addMood} onSuggested={setAiIds} onOpenModal={() => setModal(true)}
        />

        <section className="card">
          <h3>{isToday ? '오늘의 컨디션' : '이날의 컨디션'} <span className="muted small">(적은 것만 저장돼요)</span></h3>
          <div className="grid2">
            {NUM_FIELDS.map(([k, label, attrs, icon]) => (
              <label key={k}><span className="field-label"><Art name={icon} size={24} />{label}</span>
                <input type="number" inputMode="decimal" value={cond[k]} onChange={setNum(k)} {...attrs} />
              </label>
            ))}
          </div>
          <Scale label="수면의 질" icon="cond-sleep-quality" low="나쁨" high="좋음" value={cond.sleep_score} onChange={(v) => setCond((p) => ({ ...p, sleep_score: v }))} />
          <Scale label="식욕" icon="cond-appetite" low="없음" high="좋음" value={cond.appetite_score} onChange={(v) => setCond((p) => ({ ...p, appetite_score: v }))} />
          <Scale label="배변" icon="cond-bowel" low="불편" high="편안" value={cond.bowel_score} onChange={(v) => setCond((p) => ({ ...p, bowel_score: v }))} />
        </section>

        {msg && <p className={`msg ${msg.type}`} role={msg.type === 'error' ? 'alert' : 'status'}>{msg.text}</p>}
        <button className="btn primary full" disabled={saving}>{saving ? '저장 중…' : diaryId ? '수정 저장' : '저장하기'}</button>
        {diaryId && <button type="button" className="btn ghost full" onClick={startNew}>이 날 일기 하나 더 쓰기</button>}
      </form>

      <MoodSelectorModal isOpen={modal} onClose={() => setModal(false)} selectedIds={moods.map((m) => m.id)} onToggle={toggleMood} />
    </div>
  );
}
