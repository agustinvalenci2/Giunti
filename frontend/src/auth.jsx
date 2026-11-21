import {createContext, useContext, useEffect, useState} from 'react';
import {api, setCsrfToken} from './api';

const AuthContext = createContext(null);

export function AuthProvider({children}) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  function acceptSession(data) { setUser(data.user); setCsrfToken(data.csrf_token); }
  async function refresh() {
    setLoading(true); setError('');
    try { acceptSession(await api('/auth/me')); }
    catch (error) { if (error.status !== 401) setError(error.message); }
    finally { setLoading(false); }
  }
  useEffect(() => {
    refresh();
    function expire() { setUser(null); setCsrfToken(''); }
    window.addEventListener('session-expired', expire);
    return () => window.removeEventListener('session-expired', expire);
  }, []);
  async function authenticate(mode, values) { acceptSession(await api(`/auth/${mode}`, {method: 'POST', body: values})); }
  async function logout() { await api('/auth/logout', {method: 'POST'}); setUser(null); setCsrfToken(''); }
  return <AuthContext.Provider value={{user, loading, error, refresh, authenticate, logout}}>{children}</AuthContext.Provider>;
}

export function useAuth() { return useContext(AuthContext); }
