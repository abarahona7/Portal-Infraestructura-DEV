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
    expect(screen.getByRole('option', { name: 'NOTEBOOK' })).toHaveValue('Notebook');
    expect(screen.queryByRole('option', { name: 'CELULAR' })).not.toBeInTheDocument();
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
    expect(screen.getByRole('option', { name: 'MOUSE' })).toHaveValue('Mouse');
    expect(screen.queryByRole('option', { name: 'NOTEBOOK' })).not.toBeInTheDocument();
    fireEvent.change(type, { target: { value: 'Mouse' } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ tipo: 'Mouse' }));
  });

  it('dirige el hostname del Notebook asignado al usuario y conserva la licencia visible', () => {
    render(<EquipoEditForm {...props}
      equipo={{ ...props.equipo, usuario: 5, hostname: 'NB-001' }}
      usuarios={[{ id: 5, nombre_completo: 'Persona', usuario_red: 'persona', estado: 'LICENCIA' }]}
      category="Notebook" />);
    expect(screen.getByRole('textbox', { name: 'Hostname' })).toBeDisabled();
    expect(screen.getByText(/Edita el hostname desde el usuario asignado/)).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Usuario asignado' })).toHaveValue('5');
    expect(screen.getByRole('option', { name: /En licencia/ })).toBeInTheDocument();
  });

  it.each(['Notebook', 'Mac'])(
    'muestra el hostname real al asignar un %s a un usuario',
    (type) => {
      const onChange = vi.fn();
      const usuarios = [{
        id: 7, nombre_completo: 'Persona', usuario_red: 'persona',
        estado: 'ACTIVO', hostname: 'HOST-007',
      }];
      const view = render(<EquipoCreateForm {...props}
        equipo={{ tipo: type, marca: 'Marca', modelo: 'Modelo' }}
        usuarios={usuarios} onChange={onChange} category={type} />);
      fireEvent.change(screen.getByRole('combobox', { name: 'Usuario asignado' }), {
        target: { value: '7' },
      });
      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
        usuario: '7', hostname: 'HOST-007',
      }));
      view.unmount();

      render(<EquipoEditForm {...props}
        equipo={{ tipo: type, marca: 'Marca', modelo: 'Modelo' }}
        usuarios={usuarios} onChange={onChange} category={type} />);
      fireEvent.change(screen.getByRole('combobox', { name: 'Usuario asignado' }), {
        target: { value: '7' },
      });
      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
        usuario: '7', hostname: 'HOST-007',
      }));
    }
  );
});
