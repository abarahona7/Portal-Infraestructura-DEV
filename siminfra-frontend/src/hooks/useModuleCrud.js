import { createItemByTab } from '../services/createItemService';
import { updateItemByTab } from '../services/updateItemService';
import { deleteItemByTab } from '../services/deleteItemService';
import { getItemDetailsByTab } from '../services/getItemService';

import { prepareCreatePayload } from '../utils/prepareCreatePayload';
import { prepareUpdatePayload } from '../utils/prepareUpdatePayload';
import { validateItem } from '../utils/validateItem';
import { formatEquipmentType } from '../utils/formatEquipmentType';
import { equipmentChecklist, needsEquipmentChecklist } from '../utils/changeProtocols';

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

const getUpdateConfirmation = (tab, editingItem, originalItem) => {
  const defaultConfirmation = {
    title: 'Guardar cambios',
    message: '¿Confirmas que deseas guardar los cambios realizados?',
    confirmText: 'Guardar',
  };

  if (!editingItem?.id) {
    return defaultConfirmation;
  }

  if (tab === 'equipos' && needsEquipmentChecklist(originalItem, editingItem)) {
    return {
      title: 'Confirmar movimiento del equipo',
      message: 'Revisa y confirma cada punto antes de guardar el cambio.',
      confirmText: 'Guardar movimiento',
      checklist: equipmentChecklist,
    };
  }
  if (tab !== 'usuarios') return defaultConfirmation;
  const nextStatus = editingItem.estado;
  const isStatusChange = originalItem?.estado !== nextStatus;

  if (!isStatusChange) {
    return defaultConfirmation;
  }

  if (nextStatus === 'BAJA') {
    return {
      title: 'Confirmar Baja del usuario',
      message: 'Revisa las asignaciones actuales antes de confirmar la baja.',
      checklist: originalItem.protocolos_estado?.BAJA || [],
      confirmText: 'Guardar Baja',
      danger: true,
    };
  }

  if (nextStatus === 'LICENCIA') {
    return {
      title: 'Guardar cambios',
      message: 'Revisa el efecto de la licencia sobre las asignaciones actuales.',
      checklist: originalItem.protocolos_estado?.LICENCIA || [],
      confirmText: 'Confirmar licencia',
      danger: true,
    };
  }

  return {
    ...defaultConfirmation,
    message: 'Confirma la revisión de datos y accesos antes de reactivar al usuario.',
    checklist: originalItem.protocolos_estado?.ACTIVO || [],
  };
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

    let originalItem = data.find((item) => String(item.id) === String(editingItem.id));
    const userStatusMayChange = tab === 'usuarios' && originalItem?.estado !== editingItem.estado;
    if (userStatusMayChange || (!originalItem && ['usuarios', 'equipos'].includes(tab))) {
      try {
        originalItem = await getItemDetailsByTab(tab, editingItem.id);
      } catch {
        showToast?.('No se pudo verificar el estado actual del registro.', 'error');
        return;
      }
    }
    if (tab === 'usuarios' && originalItem?.estado !== editingItem.estado
      && !originalItem?.protocolos_estado?.[editingItem.estado]?.length) {
      showToast?.('No se pudo cargar el protocolo actual del usuario.', 'error');
      return;
    }
    const confirmed = await requestConfirmation?.(
      getUpdateConfirmation(tab, editingItem, originalItem)
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
      if (Array.isArray(confirmed)) {
        payload.protocolo_confirmaciones = confirmed;
      }

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
      title: 'Enviar a Papelera',
      message: `¿Quieres enviar "${nombre}" a Papelera? Podrás consultar y restaurar el registro después. Las asignaciones liberadas deberán revisarse manualmente.`,
      confirmText: 'Enviar a Papelera',
      danger: true,
    });

    if (confirmed === false) {
      return;
    }

    try {
      await deleteItemByTab(tab, id);

      showToast?.(
        'Registro enviado a Papelera.',
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
