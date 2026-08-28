// Route koruma hook'u (PROMPT 8 & 12). Oturum yoksa (veya gerekli role sahip
// değilse) verilen yönlendirme callback'ini çağırır. `App.jsx`'in kendi basit
// sayfa state makinesiyle uyumlu çalışacak şekilde tasarlandı (react-router
// bağımlılığı eklemeden).
import { useEffect } from 'react';
import { useAuth } from './useAuth';

/**
 * @param {(page: string) => void} navigate - örn. App.jsx'teki setCurrentPage
 * @param {{ requireRole?: string, redirectTo?: string }} options
 */
export function useProtectedRoute(navigate, options = {}) {
  const { requireRole, redirectTo = 'login' } = options;
  const { user, isAuthenticated } = useAuth();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate(redirectTo);
      return;
    }
    if (requireRole && user?.role !== requireRole && user?.role !== 'SUPER_ADMIN') {
      navigate(redirectTo);
    }
  }, [isAuthenticated, user, requireRole, redirectTo, navigate]);

  return { user, isAuthenticated };
}
