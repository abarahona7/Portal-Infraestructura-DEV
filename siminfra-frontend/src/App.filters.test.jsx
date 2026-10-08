import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { useModuleData } from './hooks/useModuleData';

vi.mock('./hooks/useAuth', () => ({
  useAuth: () => ({
    token: 'access-test',
    user: { role: 'Administrador', username: 'qa' },
    authReady: true,
    loginError: '',
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock('./hooks/useIdleLogout', () => ({ useIdleLogout: vi.fn() }));
vi.mock('./hooks/useRealtimeChanges', () => ({ useRealtimeChanges: vi.fn() }));

vi.mock('./hooks/useReferenceData', () => ({
  useReferenceData: () => ({
    dptosList: ['TECNOLOGÍA'],
    usuariosList: [],
    usuariosStats: {
      total: 1,
      departamentos: [{ nombre: 'TECNOLOGÍA', total: 1 }],
    },
    ipsList: [],
    departamentosList: [{ id: 1, nombre: 'TECNOLOGÍA', activo: true, subareas: [] }],
    perfilesList: [{ id: 1, departamento: 1, subarea: null, estado: 'ACTIVO' }],
    ipSegmentStats: {},
    refreshReferenceData: vi.fn(),
    ensureReferenceData: vi.fn(),
    invalidateReferenceData: vi.fn(),
  }),
}));

vi.mock('./hooks/useModuleData', () => ({
  useModuleData: vi.fn(() => ({
    data: [],
    pagination: { count: 0, page: 1, pageSize: 50, totalPages: 1 },
    setPage: vi.fn(),
    refreshData: vi.fn(),
    getAllData: vi.fn(),
    isLoading: false,
  })),
}));

describe('Filtros de estado en los listados', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('muestra el listado general de usuarios sin exigir seleccionar un departamento', () => {
    render(<App />);

    expect(screen.getByText('Todos los usuarios')).toBeInTheDocument();
    expect(screen.getAllByRole('combobox', { name: 'Filtrar usuarios por estado' })).toHaveLength(1);
    expect(useModuleData).toHaveBeenCalledWith(expect.objectContaining({
      tab: 'usuarios',
      selectedDpto: '',
      enabled: true,
    }));
  });

  it('filtra usuarios después de seleccionar un departamento', () => {
    render(<App />);
    fireEvent.click(screen.getByText('TECNOLOGÍA').closest('button'));

    const status = screen.getByRole('combobox', { name: 'Filtrar usuarios por estado' });
    fireEvent.change(status, { target: { value: 'LICENCIA' } });

    expect(status).toHaveValue('LICENCIA');
    expect(useModuleData).toHaveBeenLastCalledWith(expect.objectContaining({
      tab: 'usuarios',
      selectedDpto: 'TECNOLOGÍA',
      selectedEstadoGeneral: 'LICENCIA',
    }));
  });

  it('filtra perfiles genéricos por estado', () => {
    sessionStorage.setItem('portal-infra-ti-chile-active-tab', 'perfiles');
    render(<App />);

    const status = screen.getByRole('combobox', { name: 'Filtrar perfiles por estado' });
    fireEvent.change(status, { target: { value: 'INACTIVO' } });

    expect(status).toHaveValue('INACTIVO');
    expect(useModuleData).toHaveBeenLastCalledWith(expect.objectContaining({
      tab: 'perfiles',
      selectedEstadoGeneral: 'INACTIVO',
    }));
  });

  it('filtra Notebook por departamento en vez de estado', () => {
    sessionStorage.setItem('portal-infra-ti-chile-active-tab', 'equipos-notebook');
    render(<App />);

    const department = screen.getByRole('combobox', { name: 'Filtrar equipos por departamento' });
    fireEvent.change(department, { target: { value: '1' } });

    expect(department).toHaveValue('1');
    expect(useModuleData).toHaveBeenLastCalledWith(expect.objectContaining({
      tab: 'equipos',
      equipmentCategory: 'Notebook',
      selectedDpto: '1',
    }));
    expect(screen.queryByRole('combobox', { name: /equipos por estado/i })).not.toBeInTheDocument();
  });
});
