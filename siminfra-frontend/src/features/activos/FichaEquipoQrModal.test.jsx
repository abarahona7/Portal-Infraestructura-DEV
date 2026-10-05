import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../../api/client';
import FichaEquipoQrModal from './FichaEquipoQrModal';

vi.mock('../../api/client', () => ({ default: { get: vi.fn() } }));

describe('Ficha QR', () => {
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:qa');
    URL.revokeObjectURL = vi.fn();
    apiClient.get.mockReset();
    apiClient.get.mockImplementation((path) => Promise.resolve({
      data: path.endsWith('/imagen/')
        ? new Blob(['<svg/>'], { type: 'image/svg+xml' })
        : {
          equipo: {
            id: 5, tipo: 'Notebook', marca: 'Dell', modelo: 'Latitude',
            numero_serie: 'QA-05', af: 'AF05', estado: 'STOCK',
            departamento: null, usuario_nombre: null,
          },
        },
    }));
  });

  afterEach(() => {
    delete URL.createObjectURL;
    delete URL.revokeObjectURL;
  });

  it('identifica claramente al equipo devuelto sin usuario ni departamento', async () => {
    const onClose = vi.fn();
    render(<FichaEquipoQrModal token="qa-token" onClose={onClose} onOpenHistory={vi.fn()} />);

    expect(await screen.findByText('Sin departamento asignado')).toBeInTheDocument();
    expect(screen.getByText('Sin usuario asignado')).toBeInTheDocument();
    expect(screen.getByText('Notebook · Dell Latitude')).toBeInTheDocument();
    expect(screen.queryByText(/RUT/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar ficha' }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
