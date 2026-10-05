import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../../../api/client';
import EquipoDetailModal from './EquipoDetailModal';

vi.mock('../../../api/client', () => ({ default: { get: vi.fn() } }));

const equipment = {
  id: 5, tipo: 'Notebook', marca: 'Dell', modelo: 'Latitude',
  numero_serie: 'QA-05', af: 'AF05', estado: 'STOCK',
  departamento_nombre: null, usuario_nombre: null,
};

describe('Ficha del equipo', () => {
  beforeEach(() => {
    apiClient.get.mockReset();
    apiClient.get.mockImplementation((path) => Promise.resolve({
      data: path.startsWith('/activos/qr/') ? { equipo: equipment } : equipment,
    }));
  });

  it('abre por ID y muestra el equipo devuelto sin QR', async () => {
    const onClose = vi.fn();
    const onOpenHistory = vi.fn();
    render(<EquipoDetailModal id={5} onClose={onClose} onOpenHistory={onOpenHistory} />);

    expect(await screen.findByText('Sin departamento asignado')).toBeInTheDocument();
    expect(screen.getByText('Sin usuario asignado')).toBeInTheDocument();
    expect(screen.getByText('Notebook · Dell Latitude')).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith('/equipos/5/', expect.any(Object));
    expect(screen.queryByText('Código QR')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Descargar etiqueta' })).not.toBeInTheDocument();
    expect(screen.queryByText(/RUT/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Ver historial' }));
    expect(onOpenHistory).toHaveBeenCalledWith(equipment);
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar ficha' }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('mantiene acceso a la ficha desde un enlace QR antiguo sin mostrar etiqueta', async () => {
    render(<EquipoDetailModal token="qa-token" onClose={vi.fn()} onOpenHistory={vi.fn()} />);
    expect(await screen.findByText('Notebook · Dell Latitude')).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith('/activos/qr/qa-token/', expect.any(Object));
    expect(apiClient.get).toHaveBeenCalledTimes(1);
    expect(screen.queryByText('Código QR')).not.toBeInTheDocument();
  });
});
