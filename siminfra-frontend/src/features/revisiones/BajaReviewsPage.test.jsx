import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '../../api/client';
import BajaReviewsPage from './BajaReviewsPage';

vi.mock('../../api/client', () => ({ default: { get: vi.fn(), post: vi.fn() } }));

const review = {
  id: 4,
  motivo: 'BAJA',
  usuario_nombre: 'Persona QA',
  usuario_red: 'persona.qa',
  creado_en: '2026-10-13T10:00:00Z',
  recursos: [
    { clave: 'equipo:8', tipo: 'equipo', id: 8, nombre: 'Notebook · Lenovo T14', detalle: 'REV-1' },
    { clave: 'ip:9', tipo: 'ip', id: 9, nombre: '172.23.1.233', detalle: 'Dirección IP liberada' },
  ],
};

describe('Revisiones compartidas de bajas', () => {
  beforeEach(() => {
    apiClient.get.mockReset();
    apiClient.post.mockReset();
    apiClient.get.mockResolvedValue({ data: { pendientes: 1, count: 1, page: 1, page_size: 25, results: [review] } });
    apiClient.post.mockResolvedValue({ data: { ...review, revisado_en: '2026-10-13T11:00:00Z' } });
  });

  it('abre cada recurso y exige revisar la lista completa antes de confirmar', async () => {
    const onOpenResource = vi.fn();
    render(<BajaReviewsPage revision={0} onOpenResource={onOpenResource} onCountChange={vi.fn()} showToast={vi.fn()} />);
    expect(await screen.findByText('Persona QA')).toBeInTheDocument();
    const confirmButton = screen.getByRole('button', { name: 'Confirmar revisión' });
    expect(confirmButton).toBeDisabled();
    const historyButtons = screen.getAllByRole('button', { name: 'Ver historial' });
    expect(screen.queryByRole('button', { name: 'Ver ficha' })).not.toBeInTheDocument();
    fireEvent.click(historyButtons[0]);
    fireEvent.click(historyButtons[1]);
    expect(onOpenResource).toHaveBeenNthCalledWith(1, review.recursos[0]);
    expect(onOpenResource).toHaveBeenNthCalledWith(2, review.recursos[1]);
    expect(confirmButton).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox', { name: /Confirmar Equipo/ }));
    expect(confirmButton).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox', { name: /Confirmar Dirección IP/ }));
    expect(confirmButton).toBeEnabled();
    fireEvent.click(confirmButton);
    await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith('/revisiones-baja/4/confirmar/', {
      confirmaciones: ['equipo:8', 'ip:9'],
    }));
  });

  it('identifica Licencia Médica y muestra solo la IP liberada', async () => {
    apiClient.get.mockResolvedValue({ data: {
      pendientes: 1, count: 1, page: 1, page_size: 25,
      results: [{ ...review, motivo: 'LICENCIA', recursos: [review.recursos[1]] }],
    } });
    render(<BajaReviewsPage revision={0} onOpenResource={vi.fn()} onCountChange={vi.fn()} showToast={vi.fn()} />);
    expect(await screen.findByText(/Licencia médica registrada/)).toBeInTheDocument();
    expect(screen.getByText('Dirección IP: 172.23.1.233')).toBeInTheDocument();
    expect(screen.queryByText(/Notebook · Lenovo/)).not.toBeInTheDocument();
  });
});
