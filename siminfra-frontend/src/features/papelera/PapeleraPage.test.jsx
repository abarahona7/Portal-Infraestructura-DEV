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
