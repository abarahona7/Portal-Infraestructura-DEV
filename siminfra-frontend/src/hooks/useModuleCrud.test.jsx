import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useModuleCrud } from './useModuleCrud';
import { getItemDetailsByTab } from '../services/getItemService';
import { updateItemByTab } from '../services/updateItemService';

vi.mock('../services/getItemService', () => ({ getItemDetailsByTab: vi.fn() }));
vi.mock('../services/updateItemService', () => ({ updateItemByTab: vi.fn() }));
vi.mock('../utils/validateItem', () => ({ validateItem: () => ({ valid: true }) }));

describe('Confirmación de baja del usuario', () => {
  beforeEach(() => vi.clearAllMocks());

  it('consulta las asignaciones actuales y muestra solo el protocolo que exige el backend', async () => {
    const checklist = [{
      id: 'anexo',
      label: 'Confirmé que se liberará el anexo del usuario.',
    }];
    getItemDetailsByTab.mockResolvedValue({
      id: 7,
      estado: 'ACTIVO',
      protocolos_estado: { BAJA: checklist },
    });
    updateItemByTab.mockResolvedValue({});
    const requestConfirmation = vi.fn().mockResolvedValue(['anexo']);
    const { result } = renderHook(() => useModuleCrud({
      tab: 'usuarios',
      data: [{ id: 7, estado: 'ACTIVO' }],
      editingItem: { id: 7, estado: 'BAJA' },
      refreshAllData: vi.fn().mockResolvedValue(),
      requestConfirmation,
      showToast: vi.fn(),
      setEditingItem: vi.fn(),
    }));

    await act(async () => {
      await result.current.handleSave({ preventDefault: vi.fn() });
    });

    expect(getItemDetailsByTab).toHaveBeenCalledWith('usuarios', 7);
    expect(requestConfirmation).toHaveBeenCalledWith(expect.objectContaining({ checklist }));
    expect(updateItemByTab).toHaveBeenCalledWith(
      'usuarios', 7,
      expect.objectContaining({ estado: 'BAJA', protocolo_confirmaciones: ['anexo'] }),
      undefined,
    );
  });

  it('cierra el formulario y recarga los datos ante una edición obsoleta', async () => {
    updateItemByTab.mockRejectedValue({
      response: {
        status: 409,
        data: {
          code: 'stale_update',
          detail: 'El registro fue actualizado por otra persona. Recarga los datos antes de guardar.',
        },
      },
    });
    const setEditingItem = vi.fn();
    const refreshAllData = vi.fn().mockResolvedValue();
    const showToast = vi.fn();
    const { result } = renderHook(() => useModuleCrud({
      tab: 'perfiles',
      data: [{ id: 9, version: 1, nombre: 'Perfil' }],
      editingItem: { id: 9, version: 1, nombre: 'Perfil editado' },
      refreshAllData,
      requestConfirmation: vi.fn().mockResolvedValue(true),
      showToast,
      setEditingItem,
    }));

    await act(async () => {
      await result.current.handleSave({ preventDefault: vi.fn() });
    });

    expect(setEditingItem).toHaveBeenCalledWith(null);
    expect(refreshAllData).toHaveBeenCalledOnce();
    expect(showToast).toHaveBeenCalledWith(
      'El registro fue actualizado por otra persona. Recarga los datos antes de guardar.',
      'error',
    );
  });
});
