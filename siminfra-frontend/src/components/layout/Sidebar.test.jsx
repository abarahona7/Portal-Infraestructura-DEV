import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Sidebar from './Sidebar';

const props = {
  isOpen: false,
  collapsed: false,
  activeTab: 'anexos',
  onClose: vi.fn(),
  onToggleCollapse: vi.fn(),
  onSelectTab: vi.fn(),
};

describe('Navegación por rol', () => {
  beforeEach(() => sessionStorage.clear());

  it('muestra únicamente Anexos al Visualizador', () => {
    render(<Sidebar {...props} role="Visualizador" />);
    expect(screen.getByRole('button', { name: 'Anexos' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Equipos' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Usuarios' })).not.toBeInTheDocument();
  });

  it('permite al Operador abrir Equipos y entrar al Tablero', () => {
    const onSelectTab = vi.fn();
    render(<Sidebar {...props} role="Operador Infraestructura" onSelectTab={onSelectTab} />);
    fireEvent.click(screen.getByRole('button', { name: 'Equipos' }));
    expect(onSelectTab).toHaveBeenCalledWith('equipos');
    fireEvent.click(screen.getByRole('button', { name: 'Expandir Equipos' }));
    expect(screen.queryByRole('button', { name: 'Tablero de activos' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Notebook' })).toBeInTheDocument();
  });

  it('ofrece cerrar sesión desde el sidebar y cierra el menú móvil', () => {
    const onClose = vi.fn();
    const onLogout = vi.fn();
    render(<Sidebar {...props} isOpen role="Operador Infraestructura" onClose={onClose} onLogout={onLogout} />);

    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
    expect(onClose).toHaveBeenCalledOnce();
    expect(onLogout).toHaveBeenCalledOnce();
  });
});
