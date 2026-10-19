import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../../api/client';
import AssetDashboard from './AssetDashboard';

vi.mock('../../api/client', () => ({ default: { get: vi.fn() } }));

const equipment = {
  id: 7,
  tipo: 'Notebook',
  marca: 'Dell',
  modelo: 'Latitude',
  numero_serie: '',
  af: 'AF123',
  usuario_nombre: 'Persona QA',
  estado: 'ASIGNADO',
};

const summary = {
  conteos: {
    total: 1, asignados: 1, disponibles: 0, reparacion: 0, baja: 0,
    sin_serie: 1, sin_activo_fijo: 0, sin_custodio: 0, custodio_no_activo: 0,
    custodio_baja: 0,
  },
  tipos: [{ tipo: 'Notebook', total: 1, asignados: 1 }],
  departamentos: [{ id: 3, nombre: 'Tecnología', total: 1 }],
};

describe('Tablero de activos', () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
    apiClient.get.mockReset();
    apiClient.get.mockImplementation((path) => Promise.resolve({
      data: path === '/activos/resumen/'
        ? summary
        : { count: 1, page: 1, total_pages: 1, results: [equipment] },
    }));
  });

  it('abre los equipos del departamento y permite ir a su ficha y edición', async () => {
    const onOpenAsset = vi.fn();
    const onEditAsset = vi.fn();
    render(<AssetDashboard onOpenAsset={onOpenAsset} onEditAsset={onEditAsset} />);

    fireEvent.click(await screen.findByRole('button', { name: /Tecnología/ }));
    expect(await screen.findByText('NOTEBOOK · Dell Latitude')).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith('/equipos/', expect.objectContaining({
      params: { departamento_id: 3, page: 1, page_size: 20 },
    }));
    fireEvent.click(screen.getByRole('button', { name: 'Abrir ficha de Dell Latitude' }));
    fireEvent.click(screen.getByRole('button', { name: 'Editar' }));
    expect(onOpenAsset).toHaveBeenCalledOnce();
    expect(onOpenAsset).toHaveBeenCalledWith(equipment);
    expect(onEditAsset).toHaveBeenCalledWith(equipment);
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it('muestra la lista correcta al seleccionar un pendiente', async () => {
    render(<AssetDashboard onOpenAsset={vi.fn()} onEditAsset={vi.fn()} />);

    fireEvent.click(await screen.findByRole('button', { name: /Sin número de serie/i }));
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith(
      '/equipos/', expect.objectContaining({
        params: { pendiente: 'sin_serie', page: 1, page_size: 20 },
      }),
    ));
    expect(await screen.findByText('NOTEBOOK · Dell Latitude')).toBeInTheDocument();
    expect(screen.getByText(/1 equipos/)).toBeInTheDocument();
  });

  it('abre los equipos del tipo y los indicadores de asignación y estado', async () => {
    render(<AssetDashboard onOpenAsset={vi.fn()} onEditAsset={vi.fn()} />);

    fireEvent.click(await screen.findByRole('button', { name: /NOTEBOOK.*1 con usuario/i }));
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith(
      '/equipos/', expect.objectContaining({
        params: { tipo: 'Notebook', page: 1, page_size: 20 },
      }),
    ));

    fireEvent.click(screen.getByRole('button', { name: 'Con usuario asignado: 1. Ver equipos' }));
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith(
      '/equipos/', expect.objectContaining({
        params: { asignado: 'si', page: 1, page_size: 20 },
      }),
    ));

    fireEvent.click(screen.getByRole('button', { name: 'Disponibles: 0. Ver equipos' }));
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith(
      '/equipos/', expect.objectContaining({
        params: { estado: 'STOCK', page: 1, page_size: 20 },
      }),
    ));
  });

  it('separa la alerta de usuarios de baja de los equipos sin usuario', async () => {
    apiClient.get.mockResolvedValueOnce({ data: {
      ...summary,
      conteos: { ...summary.conteos, custodio_baja: 1, sin_custodio: 2 },
    } });
    render(<AssetDashboard onOpenAsset={vi.fn()} onEditAsset={vi.fn()} />);

    const urgent = await screen.findByRole('button', { name: /Asignados a usuarios de baja/i });
    expect(urgent).toHaveClass('asset-overview-reason--urgente');
    const informational = screen.getByRole('button', { name: /Sin usuario asignado/i });
    expect(informational).toHaveClass('asset-overview-reason--informativo');
    fireEvent.click(urgent);
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith(
      '/equipos/', expect.objectContaining({
        params: { pendiente: 'custodio_baja', page: 1, page_size: 20 },
      }),
    ));
  });

  it('muestra todas las áreas devueltas por la API, incluidas las vacías', async () => {
    apiClient.get.mockResolvedValueOnce({ data: {
      ...summary,
      departamentos: [
        { id: 3, nombre: 'TECNOLOGÍA', total: 1 },
        { id: 4, nombre: 'VENTAS', total: 0 },
      ],
    } });
    render(<AssetDashboard onOpenAsset={vi.fn()} onEditAsset={vi.fn()} />);
    expect(await screen.findByRole('button', { name: /TECNOLOGÍA/ })).toBeInTheDocument();
    const zeroBar = screen.getByRole('button', { name: 'VENTAS: 0 equipos' });
    expect(zeroBar).toHaveStyle({ '--bar-width': '0%' });
    fireEvent.mouseEnter(zeroBar);
    expect(screen.getByText('VENTAS: 0 equipos')).toBeInTheDocument();
    fireEvent.mouseLeave(zeroBar);
    expect(screen.getByText('Distribución actual de equipos por área.')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Gráfico de equipos por departamento' })).toBeInTheDocument();
  });

  it('actualiza automáticamente el tablero cuando cambia la revisión', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    try {
      vi.setSystemTime(new Date('2026-10-07T12:00:00.000Z'));
      let completeRefresh;
      apiClient.get
        .mockResolvedValueOnce({ data: summary })
        .mockImplementationOnce(() => new Promise((resolve) => { completeRefresh = resolve; }));

      const props = { onOpenAsset: vi.fn(), onEditAsset: vi.fn() };
      const { container, rerender } = render(<AssetDashboard {...props} />);
      await screen.findByText(/Actualización automática/);
      const updatedAt = container.querySelector('time');
      expect(updatedAt).toHaveAttribute('dateTime', '2026-10-07T12:00:00.000Z');
      expect(screen.queryByRole('button', { name: 'Actualizar' })).not.toBeInTheDocument();

      vi.setSystemTime(new Date('2026-10-07T12:05:07.000Z'));
      rerender(<AssetDashboard {...props} revision={1} />);
      expect(screen.getByText('Sincronizando cambios...')).toBeInTheDocument();
      expect(container.querySelector('time')).not.toBeInTheDocument();

      await act(async () => { completeRefresh({ data: summary }); });
      await waitFor(() => expect(container.querySelector('time')).toHaveAttribute('dateTime', '2026-10-07T12:05:07.000Z'));
      expect(screen.getByText(/Actualización automática/)).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });
});
