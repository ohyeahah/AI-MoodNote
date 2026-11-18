// 감정을 최대 3개까지 고르고, 고른 감정들의 평균에 가장 가까운 단어를 '대표 감정'(공)으로 쓴다.
// 서버(diary.py 의 nearest_word_id)와 같은 규칙이라서 화면에서 미리 보여 주는 값과 저장되는 값이 같다.
export const MAX_MOODS = 3;

// 무드미터는 10x10 칸이 꽉 차 있고 id = (행-1)*10 + 열, 에너지 = 11-행, 쾌적도 = 열 이다.
// 에너지·쾌적도 평균을 반올림(.5 는 올림)하면 그 칸이 곧 가장 가까운 단어다.
export function nearestWordId(points) {
  const avg = (k) => points.reduce((s, w) => s + w[k], 0) / points.length;
  const clamp = (v) => Math.min(10, Math.max(1, Math.floor(v + 0.5)));
  const energy = clamp(avg('energy'));
  const pleasantness = clamp(avg('pleasantness'));
  return (11 - energy - 1) * 10 + pleasantness;
}

// moods: [{ id, ... }], byId: useMoodWords() 가 돌려주는 id → 단어. 고른 게 없거나 단어를 아직 못 받았으면 null.
export function representative(moods, byId) {
  const points = moods.map((m) => byId[m.id]).filter(Boolean);
  if (!points.length || points.length !== moods.length) return null;
  return byId[nearestWordId(points)] || null;
}
