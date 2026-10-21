import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';

const { logout } = vi.hoisted(() => ({ logout: vi.fn() }));

vi.mock('./hooks/useAuth', () => ({
  useAuth: () => ({
    token: 'viewer-token',
    user: { role: 'Visualizador', username: 'recepcion' },
    authReady: true,
    loginError: '',
    login: vi.fn(),
    logout,
  }),
}));

vi.mock('./hooks/useIdleLogout', () => ({ useIdleLogout: vi.fn() }));
vi.mock('./hooks/useRealtimeChanges', () => ({ useRealtimeChanges: vi.fn() }));

vi.mock('./hooks/useReferenceData', () => ({
  useReferenceData: () => ({
    dptosList: [], usuariosList: [], usuariosStats: { total: 0, baja: 0, departamentos: [] },
    ipsList: [], departamentosList: [], perfilesList: [], ipSegmentStats: {},
    refreshReferenceData: vi.fn(), ensureReferenceData: vi.fn(), invalidateReferenceData: vi.fn(),
  }),
}));

vi.mock('./hooks/useModuleData', () => ({
  useModuleData: () => ({
    data: [],
    pagination: { count: 0, page: 1, pageSize: 50, totalPages: 1 },
    setPage: vi.fn(), refreshData: vi.fn(), getAllData: vi.fn(), isLoading: false,
  }),
}));

describe('Vista exclusiva del Visualizador', () => {
  beforeEach(() => {
    sessionStorage.clear();
    logout.mockClear();
  });

  it('muestra Anexos a ancho completo sin sidebar ni botón de menú', async () => {
    const { container } = render(<App />);

    expect(screen.queryByRole('navigation', { name: 'Menú principal' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Abrir menú de módulos' })).not.toBeInTheDocument();
    expect(screen.getByText('Consulta de anexos asignados')).toBeInTheDocument();
    expect(screen.getByRole('searchbox', { name: /Buscar/i })).toBeInTheDocument();
    expect(container.querySelector('main')).toHaveClass('app-main-viewer');

    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
    fireEvent.click(
      within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Cerrar sesión' })
    );
    await waitFor(() => expect(logout).toHaveBeenCalledOnce());
  });
});
