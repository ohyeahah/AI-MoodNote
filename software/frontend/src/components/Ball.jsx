import React from 'react';

// 감정 공 그림. 단어 번호(1~100)가 곧 파일 번호다. (ball_001.png ~ ball_100.png)
// 공의 크기는 모두 같고, 감정의 세기는 색의 진하기(명도)로 나타낸다. 약한 감정은 연하고, 강한 감정은 진하다.
// 그림은 장식이고 감정 이름은 옆의 글자가 알려 주므로 alt 는 비워 둔다.
export const ballSrc = (id) => `/art/balls/ball_${String(id).padStart(3, '0')}.png`;

// 앱을 켜면 공 그림 100개를 한가한 때에 미리 받아 둔다. (서버가 멀어서 그림을 하나씩 받으면 공이 하나둘 늦게 뜨기 때문)
// 한 번 받은 그림은 브라우저가 기억하므로(서버의 캐시 설정), 이후에는 달력·감정 고르기 창에서 바로 보인다.
export function preloadBalls() {
  const run = () => { for (let id = 1; id <= 100; id += 1) { const img = new Image(); img.src = ballSrc(id); } };
  if ('requestIdleCallback' in window) window.requestIdleCallback(run, { timeout: 3000 });
  else setTimeout(run, 800);
}

export default function Ball({ id, size = 36, className = '' }) {
  if (!id) return null;
  return (
    <img
      className={`ball-img ${className}`} src={ballSrc(id)} width={size} height={size}
      alt="" aria-hidden="true" draggable="false"
      onError={(e) => { e.currentTarget.style.visibility = 'hidden'; }}
      onLoad={(e) => { e.currentTarget.style.visibility = 'visible'; }}   // 같은 자리에서 다른 공으로 바뀔 때, 앞서 숨겨진 상태가 남지 않게 한다
    />
  );
}
