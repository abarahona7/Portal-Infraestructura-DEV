import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import EquipoCreateForm from './EquipoCreateForm';
import EquipoEditForm from './EquipoEditForm';

const props = {
  equipo: { tipo: 'Notebook', marca: 'Dell', modelo: 'Latitude' },
  onChange: vi.fn(),
  usuarios: [],
  formatEquipmentType: (value) => value,
  onHostnameChange: vi.fn(),
};

describe('Tipo de equipo por categoría', () => {
  it('bloquea el tipo al crear y editar Notebook', () => {
    const created = render(<EquipoCreateForm {...props} category="Notebook" />);
    const type = screen.getByRole('combobox', { name: 'Tipo de equipo' });
    expect(type).toBeDisabled();
    expect(type.value).toBe('Notebook');
    expect(screen.queryByRole('option', { name: 'Celular' })).not.toBeInTheDocument();
    created.unmount();
    render(<EquipoEditForm {...props} category="Notebook" />);
    expect(screen.getByRole('combobox', { name: 'Tipo de equipo' })).toBeDisabled();
  });

  it('limita Periféricos a sus propios tipos', () => {
    const onChange = vi.fn();
    render(<EquipoCreateForm {...props} equipo={{ ...props.equipo, tipo: 'Monitor' }}
      onChange={onChange} category="PERIFERICOS" />);
    const type = screen.getByRole('combobox', { name: 'Tipo de equipo' });
    expect(type).toBeEnabled();
    expect(screen.getByRole('option', { name: 'Mouse' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Notebook' })).not.toBeInTheDocument();
    fireEvent.change(type, { target: { value: 'Mouse' } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ tipo: 'Mouse' }));
  });
});
