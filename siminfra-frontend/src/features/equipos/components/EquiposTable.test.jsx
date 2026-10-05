import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import EquiposTable from './EquiposTable';

const equipment = {
  id: 7,
  tipo: 'Notebook',
  marca: 'Dell',
  modelo: 'Latitude',
  numero_serie: 'QA-07',
  estado: 'STOCK',
};

describe('Listado de equipos', () => {
  it('abre la ficha al pulsar la fila o tarjeta, sin confundirla con editar o historial', () => {
    const onSelectEquipment = vi.fn();
    const onEdit = vi.fn();
    const onShowHistory = vi.fn();
    render(<EquiposTable
      equipos={[equipment]}
      formatEquipmentType={(type) => type}
      onSelectEquipment={onSelectEquipment}
      onShowHistory={onShowHistory}
      onEdit={onEdit}
      onDelete={vi.fn()}
      role="Administrador"
    />);

    const [row, card] = screen.getAllByRole('button', { name: 'Abrir ficha de Dell Latitude' });
    fireEvent.click(row);
    fireEvent.keyDown(row, { key: 'Enter' });
    fireEvent.click(card);
    expect(onSelectEquipment).toHaveBeenCalledTimes(3);
    expect(onSelectEquipment).toHaveBeenLastCalledWith(equipment);

    onSelectEquipment.mockClear();
    fireEvent.click(screen.getAllByRole('button', { name: 'Editar equipo' })[0]);
    fireEvent.click(screen.getAllByRole('button', { name: 'Editar equipo' })[1]);
    fireEvent.click(screen.getAllByRole('button', { name: 'Ver historial' })[0]);
    expect(onEdit).toHaveBeenCalledTimes(2);
    expect(onEdit).toHaveBeenCalledWith(equipment);
    expect(onShowHistory).toHaveBeenCalledWith(equipment);
    expect(onSelectEquipment).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: /QR/i })).not.toBeInTheDocument();
  });
});
