import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import EquipoCreateForm from './EquipoCreateForm';
import EquipoEditForm from './EquipoEditForm';
import PCGenericoCreateForm from '../../pcsGenericos/components/PCGenericoCreateForm';
import PCGenericoEditForm from '../../pcsGenericos/components/PCGenericoEditForm';

const cases = [
  ['alta de equipo', EquipoCreateForm, 'af'],
  ['edición de equipo', EquipoEditForm, 'af'],
  ['alta de PC genérico', PCGenericoCreateForm, 'activo_fijo'],
  ['edición de PC genérico', PCGenericoEditForm, 'activo_fijo'],
];

describe.each(cases)('Activo Fijo en %s', (_label, Form, field) => {
  it('conserva los ceros iniciales y descarta letras y símbolos', () => {
    const onChange = vi.fn();
    const props = field === 'af'
      ? {
        equipo: { tipo: 'Notebook', estado: 'STOCK' },
        usuarios: [], formatEquipmentType: (type) => type,
        onHostnameChange: vi.fn(), onChange,
      }
      : { pc: {}, departments: [], availableIps: [], onChange };
    render(<Form {...props} />);

    const input = screen.getByRole('textbox', { name: 'Activo fijo' });
    expect(input).toHaveAttribute('maxLength', '12');
    expect(input).toHaveAttribute('inputMode', 'numeric');
    fireEvent.change(input, { target: { value: 'AB-00123!xyz' } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      [field]: '00123',
    }));
  });
});
