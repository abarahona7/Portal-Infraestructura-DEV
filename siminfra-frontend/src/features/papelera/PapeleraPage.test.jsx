import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../../api/client';
import PapeleraPage from './PapeleraPage';

vi.mock('../../api/client', () => ({ default: { get: vi.fn(), post: vi.fn() } }));

describe('Reporte de Papelera', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    URL.createObjectURL = vi.fn(() => 'blob:papelera');
    URL.revokeObjectURL = vi.fn();
    apiClient.get.mockImplementation((path) => Promise.resolve(
      path === '/papelera/reporte/'
        ? { data: new Blob(['reporte']) }
        : { data: { results: [], page: 1, total_pages: 1, count: 0 } },
    ));
  });

  it('descarga todos los registros del módulo elegido desde el endpoint de reporte', async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    render(<PapeleraPage showToast={vi.fn()} />);

    fireEvent.change(screen.getByLabelText('Módulo'), { target: { value: 'usuarios' } });
    fireEvent.click(screen.getByRole('button', { name: 'Descargar reporte Excel' }));

    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith('/papelera/reporte/', {
      params: { modulo: 'usuarios' },
      responseType: 'blob',
    }));
    expect(click).toHaveBeenCalledOnce();
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    click.mockRestore();
  });
});

describe('Ficha de Papelera', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockImplementation((path) => Promise.resolve(path === '/papelera/'
      ? { data: { results: [{ modulo: 'usuarios', id: 19, nombre: 'Juan Pérez', eliminado_en: '2026-10-08T10:00:00Z', eliminado_por: 'admin' }], page: 1, total_pages: 1, count: 1 } }
      : { data: {
        registro: {
          nombre_completo: 'Juan Pérez', usuario_red: 'tjperez', correo_corp: 'jperez@ejemplo.cl',
          departamento: 19, departamento_nombre: 'TECNOLOGÍA', subarea: 14,
          celular: null, sif: false, hostname: 'ti25', observaciones: 'Revisar entrega',
        },
        eventos: [{ accion: 'ARCHIVO', fecha: '2026-10-08T10:00:00Z', realizado_por: 'admin', detalle: 'Registro enviado a Papelera' }],
        historial: [{ id: 1, accion: 'ARCHIVO', fecha_movimiento: '2026-10-08T10:00:00Z', observacion: 'Archivado' }],
      } }));
  });

  it('prioriza datos útiles y conserva otros datos e historiales plegados', async () => {
    render(<PapeleraPage showToast={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Ver ficha' }));

    const dialog = await screen.findByRole('dialog', { name: 'Ficha archivada' });
    expect(dialog).toHaveTextContent('TECNOLOGÍA');
    expect(dialog).toHaveTextContent('tjperez');
    expect(dialog).not.toHaveTextContent('Sin registrar');
    expect(dialog).not.toHaveTextContent('Departamento 19');
    expect(dialog).not.toHaveTextContent('Sif');
    expect(screen.getByText(/Otros datos/).closest('details')).not.toHaveAttribute('open');
    expect(screen.getByText(/Movimientos en Papelera/).closest('details')).not.toHaveAttribute('open');
    expect(screen.getByText(/Historial del módulo/).closest('details')).not.toHaveAttribute('open');
    expect(screen.getByRole('button', { name: 'Restaurar registro' })).toBeInTheDocument();
  });
});
