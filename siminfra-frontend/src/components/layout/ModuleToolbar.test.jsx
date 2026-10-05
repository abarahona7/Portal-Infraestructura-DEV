import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ModuleToolbar from './ModuleToolbar';

const props = {
  activeTab: 'anexos',
  search: '',
  onSearchChange: vi.fn(),
  selectedAnexoStatus: '',
  onAnexoStatusChange: vi.fn(),
  onCreate: vi.fn(),
  onExport: vi.fn(),
};

describe('Acciones visibles en Anexos', () => {
  it('permite consultar y filtrar sin ofrecer edición ni exportación al Visualizador', () => {
    render(<ModuleToolbar {...props} readOnly />);
    expect(screen.getByRole('searchbox', { name: /Buscar/i })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /Filtrar anexos/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Agregar Anexo/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Exportar Excel/i })).not.toBeInTheDocument();
  });

  it('permite al Operador iniciar el alta y la exportación', () => {
    const onCreate = vi.fn();
    const onExport = vi.fn();
    render(<ModuleToolbar {...props} readOnly={false} onCreate={onCreate} onExport={onExport} />);
    fireEvent.click(screen.getByRole('button', { name: /Agregar Anexo/i }));
    fireEvent.click(screen.getByRole('button', { name: /Exportar Excel/i }));
    expect(onCreate).toHaveBeenCalledOnce();
    expect(onExport).toHaveBeenCalledOnce();
  });
});
