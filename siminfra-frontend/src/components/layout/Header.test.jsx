import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Header from './Header';

describe('Notificaciones en el encabezado', () => {
  it('muestra el contador y abre la lista de liberaciones para Infraestructura', () => {
    const onOpenNotifications = vi.fn();
    render(<Header activeTab="usuarios" role="Operador Infraestructura" pendingReviewCount={2} onOpenNotifications={onOpenNotifications} />);
    fireEvent.click(screen.getByRole('button', { name: 'Notificaciones: 2 liberaciones pendientes' }));
    expect(onOpenNotifications).toHaveBeenCalledOnce();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('conserva la campana sin contador cuando no hay pendientes', () => {
    render(<Header activeTab="revisiones-baja" role="Administrador" onOpenNotifications={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Notificaciones: 0 liberaciones pendientes' })).toHaveAttribute('aria-current', 'page');
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('oculta las notificaciones al rol Visualizador', () => {
    const onLogout = vi.fn();
    render(<Header activeTab="anexos" role="Visualizador" username="recepcion" onOpenNotifications={vi.fn()} onLogout={onLogout} />);
    expect(screen.queryByRole('button', { name: /Notificaciones/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Abrir menú de módulos' })).not.toBeInTheDocument();
    expect(screen.getByText('Consulta de anexos asignados')).toBeInTheDocument();
    expect(screen.getByText('recepcion')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
    expect(onLogout).toHaveBeenCalledOnce();
  });
});
