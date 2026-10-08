import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import PCGenericoCreateForm from './PCGenericoCreateForm';
import PCGenericoEditForm from './PCGenericoEditForm';

describe('Tipo de PC Genérico', () => {
  it.each([
    ['creación', PCGenericoCreateForm],
    ['edición', PCGenericoEditForm],
  ])('mantiene bloqueado el tipo en %s', (_label, Form) => {
    render(<Form pc={{}} onChange={vi.fn()} />);
    const field = screen.getByRole('textbox', { name: 'Tipo de equipo' });
    expect(field).toBeDisabled();
    expect(field).toHaveValue('PC GENÉRICO');
  });
});
