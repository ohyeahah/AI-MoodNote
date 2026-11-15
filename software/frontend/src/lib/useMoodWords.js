import { useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../api/client';

// 100개 단어는 바뀌지 않는 참조 데이터라서 한 번만 받아 두고 계속 쓴다.
let cache = null;

export function useMoodWords() {
  const [words, setWords] = useState(cache || []);
  const [error, setError] = useState('');

  useEffect(() => {
    if (cache) return;
    apiRequest('/api/mood-words')
      .then((d) => { cache = d.mood_words; setWords(cache); })
      .catch((e) => setError(e.message));
  }, []);

  const byId = useMemo(() => Object.fromEntries(words.map((w) => [w.id, w])), [words]);
  // 한국어 이름이 같은 단어(초조한, 만족스러운)는 영어 이름을 같이 보여 줘야 구분된다.
  const duplicates = useMemo(() => {
    const seen = {}; words.forEach((w) => { seen[w.word_ko] = (seen[w.word_ko] || 0) + 1; });
    return new Set(Object.keys(seen).filter((k) => seen[k] > 1));
  }, [words]);
  return { words, byId, duplicates, error };
}
