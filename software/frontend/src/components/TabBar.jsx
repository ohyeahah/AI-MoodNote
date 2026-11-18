import React from 'react';
import { NavLink } from 'react-router-dom';
import Art from './Art';

const TABS = [
  { to: '/', label: '오늘', end: true, icon: 'today' },
  { to: '/calendar', label: '달력', icon: 'calendar' },
  { to: '/graph', label: '그래프', icon: 'graph' },
];

export default function TabBar() {
  return (
    <nav className="tabbar" aria-label="메뉴">
      {TABS.map((t) => (
        <NavLink key={t.to} to={t.to} end={t.end} className={({ isActive }) => (isActive ? 'tab active' : 'tab')}>
          {({ isActive }) => (
            <>
              <Art name={`tab-${t.icon}${isActive ? '-on' : ''}`} size={32} />
              <span>{t.label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
