import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || '/api';

const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

let accessToken = null;
let refreshPromise = null;
export const setAccessToken = (token) => { accessToken = token || null; };
export const getAccessToken = () => accessToken;

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
    ].some((url) => original?.url?.startsWith(url));
    if (error.response?.status !== 401 || original?._retry || isSessionEndpoint) {
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      if (!refreshPromise) {
        refreshPromise = axios.post(`${baseURL}/auth/refresh/`, {}, { withCredentials: true })
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
