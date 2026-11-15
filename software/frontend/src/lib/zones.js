// 무드미터 4구역. 에너지가 높으면 위쪽(레드·옐로우), 기분이 좋으면 오른쪽(옐로우·그린).
export const ZONES = {
  red: { label: '레드', desc: '에너지 높음 · 기분 불쾌', color: '#F0706A', soft: '#FDE6E4' },
  yellow: { label: '옐로우', desc: '에너지 높음 · 기분 유쾌', color: '#F2C230', soft: '#FDF3CF' },
  blue: { label: '블루', desc: '에너지 낮음 · 기분 불쾌', color: '#5B96F0', soft: '#E0ECFD' },
  green: { label: '그린', desc: '에너지 낮음 · 기분 유쾌', color: '#5CBF78', soft: '#DFF3E5' },
};
export const ZONE_ORDER = ['red', 'yellow', 'blue', 'green'];
export const zoneColor = (z) => ZONES[z]?.color ?? '#C9C2B4';
