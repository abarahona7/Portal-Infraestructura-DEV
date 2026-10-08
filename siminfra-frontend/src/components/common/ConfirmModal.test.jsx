import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ConfirmModal from './ConfirmModal';

describe('ConfirmModal con protocolo', () => {
  it('no permite confirmar hasta marcar todos los puntos y entrega sus IDs', () => {
    const onConfirm = vi.fn();
    render(<ConfirmModal
      open
      title="Confirmar movimiento"
      message="Verifica el protocolo"
      checklist={[
        { id: 'custodia', label: 'Verifiqué la custodia.' },
        { id: 'estado', label: 'Revisé el estado.' },
      ]}
      onConfirm={onConfirm}
    />);

    const confirm = screen.getByRole('button', { name: 'Confirmar' });
    expect(confirm).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Verifiqué la custodia.' }));
    expect(confirm).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Revisé el estado.' }));
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledWith(['custodia', 'estado']);
  });
});
