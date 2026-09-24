import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || '/api';

const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

let accessToken = null;
let refreshPromise = null;
let csrfPromise = null;
export const setAccessToken = (token) => { accessToken = token || null; };
export const getAccessToken = () => accessToken;

const hasCsrfCookie = () => (
  typeof document !== 'undefined'
  && document.cookie.split(';').some((cookie) => cookie.trim().startsWith('csrftoken='))
);

export const ensureCsrfToken = async () => {
  if (hasCsrfCookie()) {
    return;
  }
  if (!csrfPromise) {
    csrfPromise = apiClient
      .get('/auth/csrf/', { skipAuth: true })
      .finally(() => { csrfPromise = null; });
  }
  await csrfPromise;
};

apiClient.interceptors.request.use((config) => {
  if (accessToken && !config.skipAuth) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const isSessionEndpoint = [
      '/auth/login/',
      '/auth/refresh/',
      '/auth/logout/',
      '/auth/csrf/',
    ].some((url) => original?.url?.startsWith(url));
    if (error.response?.status !== 401 || original?._retry || isSessionEndpoint) {
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      if (!refreshPromise) {
        refreshPromise = ensureCsrfToken()
          .then(() => apiClient.post('/auth/refresh/', {}, { skipAuth: true }))
          .then(({ data }) => {
            setAccessToken(data.access);
            return data.access;
          })
          .finally(() => { refreshPromise = null; });
      }
      const freshToken = await refreshPromise;
      original.headers = original.headers || {};
      original.headers.Authorization = `Bearer ${freshToken}`;
      return apiClient(original);
    } catch (refreshError) {
      setAccessToken(null);
      return Promise.reject(refreshError);
    }
  }
);

export default apiClient;
