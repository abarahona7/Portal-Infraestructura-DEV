import { createItemByTab } from '../services/createItemService';
import { updateItemByTab } from '../services/updateItemService';
import { deleteItemByTab } from '../services/deleteItemService';

import { prepareCreatePayload } from '../utils/prepareCreatePayload';
import { prepareUpdatePayload } from '../utils/prepareUpdatePayload';
import { validateItem } from '../utils/validateItem';
import { formatEquipmentType } from '../utils/formatEquipmentType';

export const useModuleCrud = ({
  tab,
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

      await createItemByTab(tab, payload);

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
        'No se pudieron guardar los cambios. Verifique los datos ingresados.',
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

    const confirmed = await requestConfirmation?.({
      title: 'Guardar cambios',
      message: '¿Confirmas que deseas guardar los cambios realizados?',
      confirmText: 'Guardar',
    });

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
        payload
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
        'No se pudo crear el registro. Verifique los datos ingresados.',
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
        'No se pudo eliminar el registro.',
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