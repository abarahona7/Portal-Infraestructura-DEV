import { useCallback, useEffect, useState } from 'react';
import apiClient, { ensureCsrfToken, setAccessToken } from '../api/client';

const TAB_SESSION_KEY = 'portal-infra-ti-tab-session-active';
let bootstrapPromise = null;

const hasTabSession = () => {
  try {
    return sessionStorage.getItem(TAB_SESSION_KEY) === '1';
  } catch {
    return false;
  }
};

const markTabSession = () => {
  try {
    sessionStorage.setItem(TAB_SESSION_KEY, '1');
  } catch {
    // Si sessionStorage no está disponible, la sesión sigue funcionando
    // durante la carga actual gracias al access token en memoria.
  }
};

const clearTabSession = () => {
  try {
    sessionStorage.removeItem(TAB_SESSION_KEY);
  } catch {
    // Sin acción adicional.
  }
};

const requestBootstrapRefresh = () => {
  if (!bootstrapPromise) {
    bootstrapPromise = ensureCsrfToken()
      .then(() => apiClient.post('/auth/refresh/', {}, {
        headers: { 'X-Portal-Activity': '1' },
        skipAuth: true,
      }))
      .then(({ data }) => data)
      .finally(() => {
        bootstrapPromise = null;
      });
  }

  return bootstrapPromise;
};

export const useAuth = () => {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [loginError, setLoginError] = useState('');
  const [authReady, setAuthReady] = useState(false);

  const applySession = useCallback((data) => {
    const nextAccess = data?.access || null;

    setAccessToken(nextAccess);
    setToken(nextAccess);
    setUser(data?.user || null);

    if (nextAccess) {
      markTabSession();
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      await ensureCsrfToken();
      const { data } = await apiClient.post('/auth/refresh/', {}, {
        headers: { 'X-Portal-Activity': '1' },
        skipAuth: true,
      });
      applySession(data);
      return data.access;
    } catch {
      applySession(null);
      clearTabSession();
      return null;
    }
  }, [applySession]);

  useEffect(() => {
    let cancelled = false;

    const restoreSession = async () => {
      // sessionStorage sobrevive a F5, pero se elimina al cerrar la pestaña.
      // Así no guardamos el JWT en almacenamiento persistente y a la vez
      // podemos distinguir una recarga de una apertura nueva del portal.
      if (!hasTabSession()) {
        if (!cancelled) {
          setAuthReady(true);
        }
        return;
      }

      try {
        const data = await requestBootstrapRefresh();
        if (!cancelled) {
          applySession(data);
        }
      } catch {
        if (!cancelled) {
          applySession(null);
          clearTabSession();
        }
      } finally {
        if (!cancelled) {
          setAuthReady(true);
        }
      }
    };

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, [applySession]);

  const login = useCallback(async (username, password) => {
    setLoginError('');

    try {
      await ensureCsrfToken();
      const { data } = await apiClient.post('/auth/login/', {
        username,
        password,
      }, {
        skipAuth: true,
      });

      applySession(data);
      markTabSession();
      return true;
    } catch (error) {
      setLoginError(
        error?.response?.data?.detail ||
        'Credenciales inválidas. Verifica tu usuario y contraseña.'
      );
      return false;
    }
  }, [applySession]);

  const logout = useCallback(async () => {
    try {
      await ensureCsrfToken();
      await apiClient.post('/auth/logout/', {}, { skipAuth: true });
    } catch {
      // Aunque el backend no responda, limpiamos la sesión visible.
    }

    clearTabSession();
    applySession(null);
  }, [applySession]);

  return {
    token,
    user,
    authReady,
    loginError,
    login,
    logout,
    refresh,
  };
};
