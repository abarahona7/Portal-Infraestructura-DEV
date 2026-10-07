import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ModuleCreateModal from './ModuleCreateModal';
import ModuleEditModal from './ModuleEditModal';

function UserCreateHarness() {
  const [item, setItem] = useState({ estado: 'ACTIVO' });
  return <ModuleCreateModal tab="usuarios" newItem={item} setNewItem={setItem}
    onClose={vi.fn()} onSubmit={(event) => event.preventDefault()} />;
}

function ProfileEditHarness() {
  const [item, setItem] = useState({ nombre: 'Perfil previo', usuario: 'adminLocal' });
  return <ModuleEditModal tab="perfiles" editingItem={item} setEditingItem={setItem}
    onClose={vi.fn()} onSubmit={(event) => event.preventDefault()} />;
}

describe('Mayúsculas en formularios del portal', () => {
  it('convierte el cargo al escribir sin modificar el correo ni el usuario de red', () => {
    render(<UserCreateHarness />);
    fireEvent.change(screen.getByRole('textbox', { name: 'Cargo' }), {
      target: { value: 'Jefatura de tecnología' },
    });
    expect(screen.getByRole('textbox', { name: 'Cargo' })).toHaveValue('JEFATURA DE TECNOLOGÍA');

    fireEvent.change(screen.getByRole('textbox', { name: 'Usuario de red' }), {
      target: { value: 'usuarioMixto' },
    });
    expect(screen.getByRole('textbox', { name: 'Usuario de red' })).toHaveValue('usuarioMixto');

    fireEvent.change(screen.getByRole('textbox', { name: 'Correo corporativo' }), {
      target: { value: 'Usuario@empresa.cl' },
    });
    expect(screen.getByRole('textbox', { name: 'Correo corporativo' })).toHaveValue('Usuario@empresa.cl');
  });

  it('convierte el nombre del perfil al editar y conserva su identificador', () => {
    render(<ProfileEditHarness />);
    fireEvent.change(screen.getByRole('textbox', { name: 'Nombre o perfil' }), {
      target: { value: 'soporte médico' },
    });
    expect(screen.getByRole('textbox', { name: 'Nombre o perfil' })).toHaveValue('SOPORTE MÉDICO');
    expect(screen.getByRole('textbox', { name: 'Usuario del perfil' })).toHaveValue('adminLocal');
  });
});
