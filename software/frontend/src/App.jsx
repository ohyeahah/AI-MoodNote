import React from 'react';
import { Link, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import Art from './components/Art';
import TabBar from './components/TabBar';
import CalendarPage from './pages/CalendarPage';
import ConsentPage from './pages/ConsentPage';
import DayDetailPage from './pages/DayDetailPage';
import FeedbackPage from './pages/FeedbackPage';
import GraphPage from './pages/GraphPage';
import LoginPage from './pages/LoginPage';
import SettingsPage from './pages/SettingsPage';
import TodayPage from './pages/TodayPage';

function MainApp() {
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand" aria-label="MoodNote 홈"><img className="logo" src="/art/ui/logo.png" alt="MoodNote" height="38" draggable="false" /></Link>
        <Link to="/settings" className="art-btn" aria-label="설정"><Art name="icon-settings" size={36} /></Link>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<TodayPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/detail/:date" element={<DayDetailPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/feedback" element={<FeedbackPage />} />
          <Route path="*" element={<TodayPage />} />
        </Routes>
      </main>
      <TabBar />
    </div>
  );
}

// 로그인 → (동의 안 했으면) 동의 → 메인 순서로 화면을 고른다.
export default function App() {
  const { token, loading, error, retry, consents, logout } = useAuth();
  if (!token) return <LoginPage />;
  if (loading) return <main className="auth"><p className="muted">불러오는 중…</p></main>;
  if (error || !consents) {
    return (
      <main className="auth">
        <p className="msg error">{error || '정보를 불러오지 못했어요.'}</p>
        <button className="btn primary full" onClick={retry}>다시 시도</button>
        <button className="btn ghost full" onClick={logout}>로그아웃</button>
      </main>
    );
  }
  if (!consents.diary_storage.granted) return <ConsentPage />;
  return <MainApp />;
}
