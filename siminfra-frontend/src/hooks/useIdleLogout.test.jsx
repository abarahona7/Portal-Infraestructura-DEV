import { fireEvent, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useIdleLogout } from './useIdleLogout';

describe('Cierre por inactividad', () => {
  afterEach(() => vi.useRealTimers());

  it('espera 300 segundos desde la última interacción antes de cerrar', () => {
    vi.useFakeTimers();
    const onIdle = vi.fn();
    const onActivity = vi.fn();
    renderHook(() => useIdleLogout({ enabled: true, onIdle, onActivity }));

    vi.advanceTimersByTime(200_000);
    fireEvent.keyDown(window, { key: 'A' });
    vi.advanceTimersByTime(299_999);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onIdle).toHaveBeenCalledOnce();
  });
});
