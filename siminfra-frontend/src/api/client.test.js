import { afterEach, describe, expect, it, vi } from 'vitest';
import apiClient, { getAccessToken, setAccessToken } from './client';

const originalAdapter = apiClient.defaults.adapter;

afterEach(() => {
  apiClient.defaults.adapter = originalAdapter;
  setAccessToken(null);
  document.cookie = 'csrftoken=; Max-Age=0';
});

describe('Cliente API y renovación de sesión', () => {
  it('reintenta una solicitud 401 con un access nuevo obtenido por cookie', async () => {
    document.cookie = 'csrftoken=qa';
    setAccessToken('access-vencido');
    const requests = [];
    apiClient.defaults.adapter = vi.fn(async (config) => {
      requests.push({ url: config.url, authorization: config.headers.Authorization });
      if (config.url === '/auth/refresh/') {
        return { data: { access: 'access-renovado' }, status: 200, config };
      }
      if (config.headers.Authorization === 'Bearer access-vencido') {
        throw { config, response: { status: 401 } };
      }
      return { data: { count: 1 }, status: 200, config };
    });

    const response = await apiClient.get('/usuarios/');

    expect(response.data).toEqual({ count: 1 });
    expect(getAccessToken()).toBe('access-renovado');
    expect(requests).toEqual([
      { url: '/usuarios/', authorization: 'Bearer access-vencido' },
      { url: '/auth/refresh/', authorization: undefined },
      { url: '/usuarios/', authorization: 'Bearer access-renovado' },
    ]);
    expect(apiClient.defaults.withCredentials).toBe(true);
  });

  it('limpia el access cuando la renovación de la cookie falla', async () => {
    document.cookie = 'csrftoken=qa';
    setAccessToken('access-vencido');
    apiClient.defaults.adapter = vi.fn(async (config) => {
      if (config.url === '/auth/refresh/') {
        throw { config, response: { status: 401 } };
      }
      throw { config, response: { status: 401 } };
    });

    await expect(apiClient.get('/usuarios/')).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(getAccessToken()).toBeNull();
  });
});
