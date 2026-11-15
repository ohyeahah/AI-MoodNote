import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 개발 중에는 /api 요청을 Flask 서버(5001번)로 넘긴다. 그래서 CORS 설정을 건드릴 필요가 없다.
// 배포할 때는 프론트와 API를 같은 주소에서 내보내거나, .env.production 에 VITE_API_BASE 를 적는다.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,            // 같은 와이파이의 폰에서 접속하거나, 터널(임시 인터넷 주소)로 열 수 있게 한다
    allowedHosts: true,
    proxy: { '/api': 'http://127.0.0.1:5001' },
  },
});
