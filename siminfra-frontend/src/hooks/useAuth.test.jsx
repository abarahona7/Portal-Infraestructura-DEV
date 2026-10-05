import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from './useAuth';

const mocks = vi.hoisted(() => ({
  post: vi.fn(),
  ensureCsrfToken: vi.fn(),
  setAccessToken: vi.fn(),
}));

vi.mock('../api/client', () => ({
  default: { post: mocks.post },
  ensureCsrfToken: mocks.ensureCsrfToken,
  setAccessToken: mocks.setAccessToken,
}));

const tabKey = 'portal-infra-ti-tab-session-active';

describe('Restauración de sesión', () => {
  beforeEach(() => {
    sessionStorage.clear();
    mocks.post.mockReset();
    mocks.ensureCsrfToken.mockReset().mockResolvedValue(undefined);
    mocks.setAccessToken.mockReset();
  });

  afterEach(() => sessionStorage.clear());

  it('no refresca una pestaña nueva sin sesión previa', async () => {
    const { result } = renderHook(() => useAuth());
    await waitFor(() => expect(result.current.authReady).toBe(true));
    expect(result.current.token).toBeNull();
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it('renueva la sesión al recargar y mantiene el token sólo en memoria', async () => {
    sessionStorage.setItem(tabKey, '1');
    mocks.post.mockResolvedValue({ data: { access: 'token-nuevo', user: { id: 9 } } });
    const { result } = renderHook(() => useAuth());

    await waitFor(() => expect(result.current.authReady).toBe(true));
    expect(mocks.post).toHaveBeenCalledWith('/auth/refresh/', {}, {
      headers: { 'X-Portal-Activity': '1' },
      skipAuth: true,
    });
    expect(result.current.user).toEqual({ id: 9 });
    expect(mocks.setAccessToken).toHaveBeenCalledWith('token-nuevo');
    expect(sessionStorage.getItem(tabKey)).toBe('1');
    expect(sessionStorage.getItem('token-nuevo')).toBeNull();
  });

  it('limpia la marca de pestaña cuando falla la renovación', async () => {
    sessionStorage.setItem(tabKey, '1');
    mocks.post.mockRejectedValue(new Error('Sesión vencida'));
    const { result } = renderHook(() => useAuth());

    await waitFor(() => expect(result.current.authReady).toBe(true));
    expect(result.current.token).toBeNull();
    expect(sessionStorage.getItem(tabKey)).toBeNull();
    expect(mocks.setAccessToken).toHaveBeenCalledWith(null);
  });

  it('limpia la sesión local aunque falle el servidor al cerrar', async () => {
    mocks.post.mockImplementation((path) => path === '/auth/login/'
      ? Promise.resolve({ data: { access: 'token', user: { id: 9 } } })
      : Promise.reject(new Error('Sin conexión')));
    const { result } = renderHook(() => useAuth());
    await waitFor(() => expect(result.current.authReady).toBe(true));
    await act(async () => expect(await result.current.login('ana', 'clave')).toBe(true));
    expect(sessionStorage.getItem(tabKey)).toBe('1');

    await act(async () => result.current.logout());
    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
    expect(sessionStorage.getItem(tabKey)).toBeNull();
    expect(mocks.setAccessToken).toHaveBeenLastCalledWith(null);
  });
});
