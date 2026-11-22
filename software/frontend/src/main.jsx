import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { consumeSocialRedirect } from './api/client';
import { AuthProvider } from './auth/AuthContext';
import { preloadBalls } from './components/Ball';
import '@fontsource/poor-story/400.css';      // 손글씨체 (한글 글꼴 파일이 앱에 같이 들어가서 인터넷 없이도 보인다)
import './styles.css';

consumeSocialRedirect();      // 소셜 로그인에서 돌아온 경우 토큰을 먼저 저장한다. (AuthProvider 가 처음 읽을 때 이미 들어 있어야 한다)

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);

preloadBalls();
