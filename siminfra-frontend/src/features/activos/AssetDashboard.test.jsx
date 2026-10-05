import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
  token_qr: '00000000-0000-4000-8000-000000000007',
};

const summary = {
  conteos: {
    total: 1, asignados: 1, disponibles: 0, reparacion: 0, baja: 0,
    sin_serie: 1, sin_activo_fijo: 0, sin_custodio: 0, custodio_no_activo: 0,
  },
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
    const onOpenQr = vi.fn();
    const onEditAsset = vi.fn();
    render(<AssetDashboard onOpenQr={onOpenQr} onEditAsset={onEditAsset} />);

    fireEvent.click(await screen.findByRole('button', { name: /Tecnología/ }));
    expect(await screen.findByText('Notebook · Dell Latitude')).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith('/equipos/', expect.objectContaining({
      params: { departamento_id: 3, page: 1, page_size: 20 },
    }));
    fireEvent.click(screen.getByRole('button', { name: 'Ver ficha QR' }));
    fireEvent.click(screen.getByRole('button', { name: 'Editar' }));
    expect(onOpenQr).toHaveBeenCalledWith(equipment.token_qr);
    expect(onEditAsset).toHaveBeenCalledWith(equipment);
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it('muestra la lista correcta al seleccionar un pendiente', async () => {
    render(<AssetDashboard onOpenQr={vi.fn()} onEditAsset={vi.fn()} />);

    fireEvent.click(await screen.findByRole('button', { name: /Sin número de serie/ }));
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith(
      '/equipos/', expect.objectContaining({
        params: { pendiente: 'sin_serie', page: 1, page_size: 20 },
      }),
    ));
    expect(await screen.findByText('Notebook · Dell Latitude')).toBeInTheDocument();
    expect(screen.getByText('1 equipos')).toBeInTheDocument();
  });
});
