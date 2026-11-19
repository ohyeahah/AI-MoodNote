// 달력의 '코멘트'를 만든다. AI 가 아니라 기록을 세고 평균을 내는 계산이라서, 같은 기록이면 항상 같은 말이 나온다.
// 입력: 서버 /api/mood/graph 의 days 배열 (날짜별 entries, avg_energy, avg_pleasantness, condition).
// 기분(쾌적도)과 에너지는 모두 1~10 척도다.
import { ZONES, ZONE_ORDER } from './zones.js';

const BIG = 0.7;   // 평균이 이만큼 이상 다르면 "달라졌다"고 말한다
const TREND = 1;   // 한 기간 안에서 앞쪽과 뒤쪽 평균이 이만큼 다르면 "변했다"고 말한다

const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
const hasEntries = (d) => d.entries && d.entries.length > 0;

// 기록한 날 수, 기분·에너지 평균, 색(구역)별 횟수, 감정 단어별 횟수, 평균 수면을 센다.
export function summarize(days) {
  const recorded = days.filter(hasEntries).sort((a, b) => (a.date < b.date ? -1 : 1));
  const zones = { red: 0, yellow: 0, blue: 0, green: 0 };
  const words = {};
  recorded.forEach((d) => d.entries.forEach((e) => {
    zones[e.zone] += 1;
    words[e.word_ko] = (words[e.word_ko] || 0) + 1;
  }));
  const sleep = days.map((d) => d.condition?.sleep_hours).filter((v) => v !== null && v !== undefined).map(Number);
  return {
    recordedDays: recorded.length,
    pleasantness: mean(recorded.map((d) => d.avg_pleasantness)),
    energy: mean(recorded.map((d) => d.avg_energy)),
    series: recorded.map((d) => d.avg_pleasantness),     // 날짜순 기분. 한 기간 안의 흐름을 볼 때 쓴다
    zones, words,
    sleep: sleep.length >= 3 ? mean(sleep) : null,        // 3일 이상 적었을 때만 평균을 말한다
  };
}

function colorLine(s) {
  const max = Math.max(...ZONE_ORDER.map((z) => s.zones[z]));
  const top = ZONE_ORDER.filter((z) => s.zones[z] === max);
  if (top.length === ZONE_ORDER.length) return '색은 골고루 나왔어요.';
  if (top.length === 1) return `가장 자주 나온 색: ${ZONES[top[0]].label} (${ZONES[top[0]].desc})`;
  return `가장 자주 나온 색: ${top.map((z) => ZONES[z].label).join(', ')}`;
}

function wordLine(s) {
  const top = Object.entries(s.words).filter(([, n]) => n >= 2)
    .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1)).slice(0, 2);
  return top.length ? `자주 고른 감정: ${top.map(([w, n]) => `${w} ${n}번`).join(', ')}` : null;
}

// 앞 기간(지난달, 그 전 7일)과 비교한다. 앞 기간에 기록이 없으면 말하지 않는다.
function compareLine(s, p, before) {
  if (!p.recordedDays) return null;
  const dp = s.pleasantness - p.pleasantness;
  const de = s.energy - p.energy;
  const parts = [];
  if (dp >= BIG) parts.push('기분은 더 유쾌한 쪽이었어요.');
  else if (dp <= -BIG) parts.push('기분은 조금 가라앉은 쪽이었어요.');
  if (de >= BIG) parts.push('에너지는 더 높았어요.');
  else if (de <= -BIG) parts.push('에너지는 더 낮았어요.');
  if (!parts.length) return `${before}과 비슷한 흐름이에요.`;
  parts[0] = `${before}보다 ${parts[0]}`;
  return parts.join(' ');
}

// 한 기간 안에서 앞쪽 절반과 뒤쪽 절반의 기분을 비교한다. 기록이 4일 이상일 때만.
function trendLine(s) {
  if (s.series.length < 4) return null;
  const half = Math.floor(s.series.length / 2);
  const diff = mean(s.series.slice(-half)) - mean(s.series.slice(0, half));
  if (diff >= TREND) return '뒤로 갈수록 기분이 한결 유쾌해졌어요.';
  if (diff <= -TREND) return '뒤로 갈수록 기분이 조금 가라앉았어요.';
  return null;
}

function build({ basis, totalDays, days, prevDays, before, withTrend, emptyText }) {
  const s = summarize(days);
  if (!s.recordedDays) return { basis, lines: [emptyText] };
  const lines = [`${totalDays}일 중 ${s.recordedDays}일 기록했어요.`, colorLine(s)];
  const w = wordLine(s); if (w) lines.push(w);
  const t = withTrend ? trendLine(s) : null; if (t) lines.push(t);
  const c = compareLine(s, summarize(prevDays), before); if (c) lines.push(c);
  if (s.sleep !== null) lines.push(`수면 시간을 적은 날의 평균은 ${s.sleep.toFixed(1)}시간이에요.`);
  if (s.recordedDays >= 4 && s.pleasantness <= 3.5) {
    lines.push('힘든 날이 이어졌다면, 믿을 수 있는 사람에게 이야기해 보는 것도 좋아요.');
  }
  return { basis, lines };
}

// 날짜를 고르지 않았을 때: 보고 있는 달 전체. elapsedDays 는 그 달에서 지금까지 지난 날 수(이번 달은 오늘까지, 지난 달은 전부, 아직 안 온 달은 0).
export function buildMonthComment({ label, elapsedDays, days, prevDays }) {
  const basis = `${label} 기록 기준`;
  if (elapsedDays <= 0) return { basis, lines: ['아직 오지 않은 달이에요.'] };
  return build({ basis, totalDays: elapsedDays, days, prevDays, before: '지난달', withTrend: false, emptyText: '이 달에는 기록이 없어요.' });
}

// 날짜를 골랐을 때: 그날까지 최근 7일(그날 포함). 비교 대상은 그 앞의 7일이다.
export function buildWeekComment({ label, days, prevDays }) {
  return build({ basis: `${label} 기준`, totalDays: 7, days, prevDays, before: '그 전 7일', withTrend: true, emptyText: '이 기간에는 기록이 없어요.' });
}
