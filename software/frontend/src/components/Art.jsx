import React from 'react';

// 손그림 아이콘. public/art/ui 안의 파일 이름(확장자 제외)을 name 으로 쓴다.
// 글자로 뜻을 알 수 있는 곳에서는 alt 를 비워 두고(장식), 글자가 없는 아이콘 버튼은 버튼의 aria-label 이 뜻을 알려 준다.
export const artSrc = (name) => `/art/ui/${name}.png`;

export default function Art({ name, size = 24, className = '', alt = '' }) {
  return (
    <img
      className={`art ${className}`} src={artSrc(name)} width={size} height={size}
      alt={alt} aria-hidden={alt ? undefined : 'true'} draggable="false"
    />
  );
}
