import { createItemByTab } from '../services/createItemService';
import { updateItemByTab } from '../services/updateItemService';
import { deleteItemByTab } from '../services/deleteItemService';

import { prepareCreatePayload } from '../utils/prepareCreatePayload';
import { prepareUpdatePayload } from '../utils/prepareUpdatePayload';
import { validateItem } from '../utils/validateItem';
import { formatEquipmentType } from '../utils/formatEquipmentType';

const extractApiErrorMessage = (error, fallback) => {
  const data = error?.response?.data;

  if (!data) return fallback;
  if (typeof data === 'string') return data;
  if (typeof data.detail === 'string') return data.detail;

  for (const value of Object.values(data)) {
    if (typeof value === 'string') return value;
    if (Array.isArray(value) && value.length > 0) {
      const first = value[0];
      if (typeof first === 'string') return first;
      if (first?.string) return first.string;
    }
  }

  return fallback;
};

const getUpdateConfirmation = (tab, editingItem, data) => {
  const defaultConfirmation = {
    title: 'Guardar cambios',
    message: '¿Confirmas que deseas guardar los cambios realizados?',
    confirmText: 'Guardar',
  };

  if (tab !== 'usuarios' || !editingItem?.id) {
    return defaultConfirmation;
  }

  const originalItem = data.find(
    (item) => String(item.id) === String(editingItem.id)
  );
  const nextStatus = editingItem.estado;
  const isStatusChange = originalItem?.estado !== nextStatus;

  if (!isStatusChange) {
    return defaultConfirmation;
  }

  if (nextStatus === 'BAJA') {
    return {
      title: 'Guardar cambios',
      message: (
        'Al dar de baja al usuario se realizarán estas acciones:\n\n'
        + '• Se desasignarán sus equipos e insumos.\n'
        + '• Se liberará su dirección IP.\n'
        + '• Se liberará su anexo.\n\n'
        + 'Antes de confirmar, valida la devolución física de los equipos e insumos.'
      ),
      confirmText: 'Dar de baja',
      danger: true,
    };
  }

  if (nextStatus === 'LICENCIA') {
    return {
      title: 'Guardar cambios',
      message: (
        'Al cambiar el estado a Licencia Médica se liberará la dirección IP del usuario.\n\n'
        + 'Los equipos, insumos y el anexo permanecerán asignados.'
      ),
      confirmText: 'Confirmar licencia',
      danger: true,
    };
  }

  return defaultConfirmation;
};

export const useModuleCrud = ({
  tab,
  equipmentCategory,
  data,
  newItem,
  editingItem,
  setNewItem,
  setEditingItem,
  refreshAllData,
  showToast,
  requestConfirmation,
}) => {
  const handleCreateSave = async (e) => {
    e.preventDefault();

    const validation = validateItem(
      tab,
      newItem,
      data
    );

    if (!validation.valid) {
      showToast?.(
        validation.message,
        'error'
      );
      return;
    }

    const confirmed = await requestConfirmation?.({
      title: 'Crear registro',
      message: '¿Confirmas que deseas crear este registro?',
      confirmText: 'Crear',
    });

    if (confirmed === false) {
      return;
    }

    try {
      const payload = prepareCreatePayload(
        tab,
        newItem
      );

      await createItemByTab(tab, payload, equipmentCategory);

      showToast?.(
        'Registro creado correctamente.',
        'success'
      );

      setNewItem(null);

      try {
        await refreshAllData();
      } catch (refreshError) {
        console.error(
          'Registro creado, pero ocurrió un error actualizando los datos:',
          refreshError
        );
      }
    } catch (error) {
      console.error(
        'Error al guardar:',
        error.response?.data || error
      );

      showToast?.(
        extractApiErrorMessage(
          error,
          'No se pudo crear el registro. Verifique los datos ingresados.'
        ),
        'error'
      );
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();

    const validation = validateItem(
      tab,
      editingItem,
      data
    );

    if (!validation.valid) {
      showToast?.(
        validation.message,
        'error'
      );
      return;
    }

    const confirmed = await requestConfirmation?.(
      getUpdateConfirmation(tab, editingItem, data)
    );

    if (confirmed === false) {
      return;
    }

    try {
      const payload = prepareUpdatePayload(
        tab,
        editingItem,
        formatEquipmentType
      );

      await updateItemByTab(
        tab,
        editingItem.id,
        payload,
        equipmentCategory
      );

      showToast?.(
        'Cambios guardados correctamente.',
        'success'
      );

      setEditingItem(null);

      try {
        await refreshAllData();
      } catch (refreshError) {
        console.error(
          'Registro actualizado, pero ocurrió un error actualizando los datos:',
          refreshError
        );
      }
    } catch (error) {
      console.error(
        'Error guardando cambios:',
        error.response?.data || error
      );

      showToast?.(
        extractApiErrorMessage(
          error,
          'No se pudieron guardar los cambios. Verifique los datos ingresados.'
        ),
        'error'
      );
    }
  };

  const handleDelete = async (id, nombre) => {
    const confirmed = await requestConfirmation?.({
      title: 'Eliminar registro',
      message: `¿Estás seguro de que deseas eliminar permanentemente "${nombre}"?`,
      confirmText: 'Eliminar',
      danger: true,
    });

    if (confirmed === false) {
      return;
    }

    try {
      await deleteItemByTab(tab, id);

      showToast?.(
        'Registro eliminado correctamente.',
        'success'
      );

      try {
        await refreshAllData();
      } catch (refreshError) {
        console.error(
          'Registro eliminado, pero ocurrió un error actualizando los datos:',
          refreshError
        );
      }
    } catch (error) {
      console.error(
        'Error al eliminar registro:',
        error.response?.data || error
      );

      showToast?.(
        extractApiErrorMessage(
          error,
          'No se pudo eliminar el registro.'
        ),
        'error'
      );
    }
  };

  return {
    handleCreateSave,
    handleSave,
    handleDelete,
  };
};
