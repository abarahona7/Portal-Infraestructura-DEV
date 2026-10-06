import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import UsuarioCreateForm from './UsuarioCreateForm';
import UsuarioEditForm from './UsuarioEditForm';
import UsuariosTable from './UsuariosTable';
import { getCorporateLineNumbers } from '../../../utils/userCorporateLines';

describe('Línea móvil del usuario', () => {
  it('permite registrar una línea sin crear un equipo', () => {
    const onChange = vi.fn();
    render(<UsuarioCreateForm usuario={{ estado: 'ACTIVO' }} onChange={onChange} />);

    fireEvent.change(screen.getByRole('textbox', { name: 'Línea móvil corporativa' }), {
      target: { value: '56 9 1234-5678' },
    });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      celular: '+56912345678',
    }));
  });

  it('muestra la línea del usuario aunque no tenga celular asignado', () => {
    const usuario = {
      id: 1, nombre_completo: 'Persona Prueba', usuario_red: 'prueba',
      celular: '+56912345678', equipos: [], estado: 'ACTIVO',
    };
    render(<UsuariosTable usuarios={[usuario]} renderStatusBadge={() => 'Activo'} />);
    expect(screen.getAllByText('+56912345678').length).toBeGreaterThan(0);
  });

  it('conserva el número del equipo como referencia y no lo duplica', () => {
    const usuario = {
      celular: '+56912345678',
      equipos: [{ tipo: 'Celular', numero_telefono: '+56912345678' }],
    };
    expect(getCorporateLineNumbers(usuario)).toEqual(['+56912345678']);
    expect(getCorporateLineNumbers({ equipos: usuario.equipos })).toEqual(['+56912345678']);

    render(<UsuarioEditForm usuario={usuario} onChange={vi.fn()} />);
    expect(screen.getByRole('textbox', { name: 'Línea móvil corporativa' })).toHaveValue('+56912345678');
    expect(screen.getByText(/El equipo asignado registra:/)).toBeInTheDocument();
  });
});
