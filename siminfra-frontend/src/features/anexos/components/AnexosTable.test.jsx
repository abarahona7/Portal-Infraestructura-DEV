import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import AnexosTable from './AnexosTable';

const anexo = {
  id: 12,
  numero_anexo: '8123',
  usuario_nombre: 'PERSONA QA',
  departamento: 'TECNOLOGÍA',
  cargo: 'ANALISTA',
  exterior: '+56221234567',
  correo: 'persona.qa@example.cl',
  estado: 'ASIGNADO',
  observaciones: 'PRUEBA',
};

const renderTable = (role) => render(
  <AnexosTable
    anexos={[anexo]}
    renderAnexoStatusBadge={(status) => status}
    onShowHistory={vi.fn()}
    onEdit={vi.fn()}
    role={role}
  />
);

describe('Permisos visuales del listado de anexos', () => {
  it('muestra solo información al Visualizador', () => {
    renderTable('Visualizador');

    expect(screen.getAllByText('PERSONA QA')).toHaveLength(2);
    expect(screen.queryByText('Acciones')).not.toBeInTheDocument();
    expect(screen.queryByText('Observaciones')).not.toBeInTheDocument();
    expect(screen.queryByText('PRUEBA')).not.toBeInTheDocument();
    expect(screen.queryByText('Gestión de anexo')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Ver historial' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Editar anexo' })).not.toBeInTheDocument();
  });

  it('mantiene historial y edición para el Operador', () => {
    renderTable('Operador Infraestructura');

    expect(screen.getByText('Acciones')).toBeInTheDocument();
    expect(screen.getAllByText('Observaciones')).toHaveLength(2);
    expect(screen.getAllByText('PRUEBA')).toHaveLength(2);
    expect(screen.getAllByRole('button', { name: 'Ver historial' })).toHaveLength(2);
    expect(screen.getAllByRole('button', { name: 'Editar anexo' })).toHaveLength(2);
  });
});
