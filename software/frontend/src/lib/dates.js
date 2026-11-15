// 날짜는 모두 'YYYY-MM-DD' 문자열로 다룬다. 서버가 한국 시간 기준이라 '오늘'도 한국 시간으로 계산한다.
// (toISOString() 은 UTC 라서 한국에서 0~9시에 어제 날짜가 나온다. 그래서 쓰지 않는다.)
const kst = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul' });
export const todayKST = () => kst.format(new Date());

export const pad = (n) => String(n).padStart(2, '0');
export const ymd = (y, m, d) => `${y}-${pad(m)}-${pad(d)}`;
export const daysInMonth = (y, m) => new Date(y, m, 0).getDate();          // m: 1~12
export const firstWeekday = (y, m) => new Date(y, m - 1, 1).getDay();      // 0=일요일

const toUTC = (s) => { const [y, m, d] = s.split('-').map(Number); return Date.UTC(y, m - 1, d); };
export const addDays = (s, n) => new Date(toUTC(s) + n * 86400000).toISOString().slice(0, 10);
export const daysBetween = (a, b) => Math.round((toUTC(b) - toUTC(a)) / 86400000);

const WEEK = ['일', '월', '화', '수', '목', '금', '토'];
export function formatKo(s) {
  const dt = new Date(toUTC(s));
  return `${dt.getUTCMonth() + 1}월 ${dt.getUTCDate()}일 (${WEEK[dt.getUTCDay()]})`;
}
export const WEEKDAYS = WEEK;
