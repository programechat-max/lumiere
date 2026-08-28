// Kimlik doğrulama durumu hook'u (PROMPT 8). App.jsx'in mevcut sayfa/state
// yönetimini KIRMADAN, yeni ekranların (admin dashboard, ayarlar vb.)
// authService üzerinden tutarlı bir şekilde oturum durumuna erişebilmesi için.
import { useCallback, useEffect, useState } from 'react';
import * as authService from '../services/authService';

export function useAuth() {
  const [user, setUser] = useState(() => authService.getStoredUser());
  const [isAuthenticated, setIsAuthenticated] = useState(() => authService.isAuthenticated());

  useEffect(() => {
    const handleExpired = () => {
      setUser(null);
      setIsAuthenticated(false);
    };
    window.addEventListener('lumiere:session-expired', handleExpired);
    return () => window.removeEventListener('lumiere:session-expired', handleExpired);
  }, []);

  const login = useCallback(async (email, password) => {
    const loggedInUser = await authService.login(email, password);
    setUser(loggedInUser);
    setIsAuthenticated(true);
    return loggedInUser;
  }, []);

  const register = useCallback(async (fullName, email, password) => {
    const newUser = await authService.register(fullName, email, password);
    setUser(newUser);
    setIsAuthenticated(true);
    return newUser;
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  return { user, isAuthenticated, login, register, logout };
}
