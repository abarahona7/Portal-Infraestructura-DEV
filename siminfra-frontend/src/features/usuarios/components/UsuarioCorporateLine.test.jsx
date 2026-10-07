import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import UsuarioCreateForm from './UsuarioCreateForm';
import UsuarioEditForm from './UsuarioEditForm';
import UsuariosTable from './UsuariosTable';
import { getCorporateLineNumbers } from '../../../utils/userCorporateLines';
import { prepareUpdatePayload } from '../../../utils/prepareUpdatePayload';

describe('Línea móvil del usuario', () => {
  it('permite registrar una línea sin crear un equipo', () => {
    const onChange = vi.fn();
    render(<UsuarioCreateForm usuario={{ estado: 'ACTIVO' }} onChange={onChange} />);

    expect(screen.getByRole('combobox', { name: 'Estado del usuario' })).toHaveValue('ACTIVO');
    expect(screen.getByText('+569')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('textbox', { name: 'Nombre completo' }), {
      target: { value: 'María Pérez' },
    });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      nombre_completo: 'MARÍA PÉREZ',
    }));

    fireEvent.change(screen.getByRole('textbox', { name: 'Línea móvil corporativa' }), {
      target: { value: '12345678' },
    });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      celular: '+56912345678',
    }));

    fireEvent.paste(screen.getByRole('textbox', { name: 'Línea móvil corporativa' }), {
      clipboardData: { getData: () => '+56987654321' },
    });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      celular: '+56987654321',
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
    expect(screen.getByRole('textbox', { name: 'Línea móvil corporativa' })).toHaveValue('12345678');
    expect(screen.getByText(/también se actualizará en Celular/)).toBeInTheDocument();
  });

  it('muestra y permite cambiar una línea que solo existe en el celular asignado', () => {
    const onChange = vi.fn();
    const usuario = {
      id: 7, celular: null,
      equipos: [{ tipo: 'Celular', numero_telefono: '+56911111111' }],
    };
    render(<UsuarioEditForm usuario={usuario} onChange={onChange} />);
    const input = screen.getByRole('textbox', { name: 'Línea móvil corporativa' });
    expect(input).toHaveValue('11111111');
    fireEvent.change(input, { target: { value: '22222222' } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ celular: '+56922222222' }));

    fireEvent.change(input, { target: { value: '' } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ celular: '' }));

    expect(prepareUpdatePayload('usuarios', usuario)).not.toHaveProperty('celular');
    expect(prepareUpdatePayload('usuarios', { ...usuario, celular: '' })).toHaveProperty('celular', '');
  });

  it('distingue dos celulares diferentes de una línea adicional del usuario', () => {
    const usuario = {
      id: 8, celular: null,
      equipos: [
        { tipo: 'Celular', numero_telefono: '+56911111111' },
        { tipo: 'Celular', numero_telefono: '+56922222222' },
        { tipo: 'Tablet', numero_telefono: '+56933333333' },
      ],
    };
    expect(getCorporateLineNumbers(usuario)).toEqual(['+56911111111', '+56922222222']);
    render(<UsuarioEditForm usuario={usuario} onChange={vi.fn()} />);
    expect(screen.getByRole('textbox', { name: 'Línea adicional del usuario' })).toHaveValue('');
    expect(screen.getByText('Celulares asignados: +56911111111 · +56922222222')).toBeInTheDocument();
    expect(screen.getByText(/Cambia cada uno en Celular/)).toBeInTheDocument();
  });

  it('identifica cuál de dos líneas está vinculada al campo del usuario', () => {
    const usuario = {
      id: 9, celular: '+56911111111',
      equipos: [
        { tipo: 'Celular', numero_telefono: '+56911111111' },
        { tipo: 'Celular', numero_telefono: '+56922222222' },
      ],
    };
    render(<UsuarioEditForm usuario={usuario} onChange={vi.fn()} />);
    expect(screen.getByRole('textbox', { name: 'Línea móvil corporativa' })).toHaveValue('11111111');
    expect(screen.getByText(/actualizará el celular que usa ese número/)).toBeInTheDocument();
  });
});
