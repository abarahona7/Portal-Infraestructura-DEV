import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useRealtimeChanges } from './useRealtimeChanges';

vi.mock('../api/client', () => ({
  default: { defaults: { baseURL: '/api' }, get: vi.fn() },
  getAccessToken: () => 'access-qa',
}));

let sockets;

class FakeSocket {
  constructor(url) {
    this.url = url;
    this.send = vi.fn();
    sockets.push(this);
  }

  close() { this.onclose?.({ code: 1000 }); }
  open() { this.onopen?.(); }
  message(value) { this.onmessage?.({ data: JSON.stringify(value) }); }
  disconnect() { this.onclose?.({ code: 1006 }); }
}

describe('Sincronización entre pestañas y usuarios', () => {
  beforeEach(() => {
    sockets = [];
    vi.useFakeTimers();
    vi.stubGlobal('WebSocket', FakeSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('agrupa eventos cercanos y reconecta una sola vez', () => {
    const onChanges = vi.fn();
    const onReconnect = vi.fn();
    const { unmount } = renderHook(() => useRealtimeChanges({
      enabled: true, onChanges, onReconnect,
    }));

    expect(sockets).toHaveLength(1);
    expect(sockets[0].url).toBe('ws://localhost/ws/changes/');
    act(() => {
      sockets[0].open();
      sockets[0].message({ type: 'ready' });
      sockets[0].message({ type: 'change', event_id: '1', modules: ['equipos', 'usuarios'] });
      sockets[0].message({ type: 'change', event_id: '1', modules: ['equipos'] });
      sockets[0].message({ type: 'change', event_id: '2', modules: ['usuarios'] });
      vi.advanceTimersByTime(150);
    });
    expect(sockets[0].send).toHaveBeenCalledWith(JSON.stringify({ type: 'auth', token: 'access-qa' }));
    expect(onChanges).toHaveBeenCalledOnce();
    expect(onChanges).toHaveBeenCalledWith(['equipos', 'usuarios']);

    act(() => {
      sockets[0].disconnect();
      vi.advanceTimersByTime(2000);
    });
    expect(sockets).toHaveLength(2);
    act(() => {
      sockets[1].open();
      sockets[1].message({ type: 'ready' });
    });
    expect(onReconnect).toHaveBeenCalledOnce();
    unmount();
  });
});
