import React from 'react';
import { NavLink } from 'react-router-dom';

const TABS = [
  { to: '/', label: '오늘', end: true },
  { to: '/calendar', label: '달력' },
  { to: '/graph', label: '그래프' },
];

export default function TabBar() {
  return (
    <nav className="tabbar" aria-label="메뉴">
      {TABS.map((t) => (
        <NavLink key={t.to} to={t.to} end={t.end} className={({ isActive }) => (isActive ? 'tab active' : 'tab')}>{t.label}</NavLink>
      ))}
    </nav>
  );
}
