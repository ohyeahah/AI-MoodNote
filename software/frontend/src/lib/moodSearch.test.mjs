// 실행: node src/lib/moodSearch.test.mjs   (mood_words.csv 는 backend 의 것을 그대로 쓴다)
import fs from 'node:fs';
import assert from 'node:assert/strict';
import { searchMoods } from './moodSearch.js';

const csvPath = process.argv[2] || new URL('../../../backend/mood_words.csv', import.meta.url);
const rows = fs.readFileSync(csvPath, 'utf8').replace(/^﻿/, '').trim().split(/\r?\n/).slice(1);
const words = rows.map((r) => {
  const [id, word_ko, word_en, grid_row, grid_col, energy, pleasantness, zone] = r.split(',');
  return { id: +id, word_ko: word_ko.trim(), word_en, grid_row: +grid_row, grid_col: +grid_col, energy: +energy, pleasantness: +pleasantness, zone };
});
assert.equal(words.length, 100);
const names = (a) => a.map((w) => w.word_ko).join(', ');
const idsOf = (q) => { const r = searchMoods(q, words); return { best: r.best.map((w) => w.id), similar: r.similar.map((w) => w.id), r }; };

// 단어 그대로
assert.equal(idsOf('슬픈').best[0], 64);
assert.equal(idsOf('Sad').best[0], 64);
assert.equal(idsOf('calm').best[0], 66);
assert.equal(idsOf('평온').best[0], 66);
assert.equal(idsOf('피곤한').best[0], 75);
// 같은 이름 두 개는 둘 다 나온다
assert.deepEqual(idsOf('초조한').best.slice(0, 2).sort((a, b) => a - b), [4, 24]);
assert.ok(idsOf('만족스러운').best.includes(36) && idsOf('만족스러운').best.includes(68));
// 일상 표현
const cases = {
  '외로워': 73, '외로워요 ㅠㅠ': 73, '설레': 28, '설레요': 28, '피곤해': 75, '피곤해요': 75, '우울해': 82,
  '화났어': 23, '짜증나': 34, '불안해': 31, '걱정돼': 33, '행복해': 38, '감사해': 69, '뿌듯해': 39,
  '심심해': 65, '졸려': 96, '긴장돼': 24, '무서워': 22, '슬퍼': 64, '속상해': 53, '억울해': 13, '답답해': 13,
  '평화로워': 88, '편안해': 78, '지쳤어': 85, '무기력해': 54, '배고프다': 34, '화': 23, '놀랐어': 6, '당황스러워': 15,
};
for (const [q, id] of Object.entries(cases)) {
  const { best } = idsOf(q);
  assert.ok(best.includes(id), `"${q}" → ${names(searchMoods(q, words).best)} (기대: ${words[id - 1].word_ko})`);
}
// 비슷한 감정: 찾은 단어 옆 칸이 나온다 (64 슬픈 → 63, 65, 54, 74 ...)
const sad = idsOf('슬픈');
assert.ok(sad.best.length + sad.similar.length >= 4);
// 규칙: 빈 입력, 의미 없는 입력은 비어 있어야 한다
assert.deepEqual(searchMoods('', words), { best: [], similar: [] });
assert.deepEqual(searchMoods('   ', words), { best: [], similar: [] });
assert.deepEqual(searchMoods('ㅋㅋㅋㅋ', words), { best: [], similar: [] });
assert.deepEqual(searchMoods('xyzqq', words), { best: [], similar: [] });
// 한 글자 말은 다른 말에 끼어 걸리지 않는다 ("평화로운" 안의 '화' 는 화난 쪽을 부르면 안 된다)
assert.ok(!idsOf('평화로운').best.includes(23));
// 결과 개수 상한, 같은 단어가 best 와 similar 에 같이 나오지 않는다
for (const q of ['외로워', '화났어', '피곤해', '설레']) {
  const { best, similar } = idsOf(q);
  assert.ok(best.length <= 4 && similar.length <= 4);
  assert.equal(new Set([...best, ...similar]).size, best.length + similar.length);
}
for (const q of ['외로워', '설레', '피곤해', '배고프다', '화']) {
  const r = searchMoods(q, words);
  console.log(`${q.padEnd(6)} → 가까운: ${names(r.best)} | 비슷한: ${names(r.similar)}`);
}
console.log('all moodSearch tests passed');
