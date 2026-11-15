import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { apiRequest, getToken, setToken } from '../api/client';

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export const CONSENT_VERSION = 'v1';

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(getToken());
  const [user, setUser] = useState(null);
  const [consents, setConsents] = useState(null);
  const [loading, setLoading] = useState(!!getToken());
  const [error, setError] = useState('');

  const logout = useCallback(() => {
    setToken(null); setTokenState(null); setUser(null); setConsents(null); setError('');
  }, []);

  const refresh = useCallback(async () => {
    const [me, c] = await Promise.all([apiRequest('/api/users/me'), apiRequest('/api/consents')]);
    setUser(me.user);
    setConsents(c.consents);
  }, []);

  const load = useCallback(() => {
    setLoading(true); setError('');
    return refresh().catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [refresh]);

  useEffect(() => {                       // 다른 곳에서 토큰 만료를 알리면 로그아웃
    window.addEventListener('auth:expired', logout);
    return () => window.removeEventListener('auth:expired', logout);
  }, [logout]);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    load();
  }, [token, load]);

  const login = async (loginId, password) => {
    const r = await apiRequest('/api/auth/login', { method: 'POST', body: JSON.stringify({ login_id: loginId, password }) });
    setToken(r.access_token);
    setTokenState(r.access_token);
  };

  const signup = async (loginId, nickname, password) => {
    await apiRequest('/api/auth/signup', { method: 'POST', body: JSON.stringify({ login_id: loginId, nickname, password }) });
    await login(loginId, password);
  };

  const setConsent = async (type, granted) => {
    await apiRequest(`/api/consents/${type}`, {
      method: 'PUT',
      body: JSON.stringify(granted ? { granted: true, version: CONSENT_VERSION } : { granted: false }),
    });
    await refresh();
  };

  const value = { token, user, consents, loading, error, retry: load, login, signup, logout, refresh, setConsent };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
