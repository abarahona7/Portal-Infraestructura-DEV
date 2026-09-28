import { useMemo, useState } from 'react';
import {
  Building2,
  CheckCircle2,
  Layers3,
  Pencil,
  Plus,
  Power,
  Search,
  Trash2,
} from 'lucide-react';

import CreateModal from '../../../components/common/CreateModal';
import EditModal from '../../../components/common/EditModal';
import {
  createDepartamento,
  createSubarea,
  deleteDepartamento,
  deleteSubarea,
  updateDepartamento,
  updateSubarea,
} from '../../../api/departamentosApi';

import './DepartamentosSubareasPage.css';

const normalize = (value = '') =>
  value.trim().replace(/\s+/g, ' ').toLocaleLowerCase('es');

const getApiErrorMessage = (error) => {
  const data = error?.response?.data;

  if (!data) {
    return 'No fue posible completar la operación.';
  }

  if (typeof data === 'string') {
    return data;
  }

  const firstValue = Object.values(data)[0];

  if (Array.isArray(firstValue) && firstValue[0]) {
    return String(firstValue[0]);
  }

  if (typeof firstValue === 'string') {
    return firstValue;
  }

  return 'No fue posible completar la operación. Verifique los datos ingresados.';
};

export default function DepartamentosSubareasPage({
  departamentos = [],
  onRefresh,
  showToast,
  requestConfirmation,
  role,
}) {
  const [selectedDepartmentId, setSelectedDepartmentId] = useState(null);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(null);
  const [saving, setSaving] = useState(false);
  const canDelete = role === 'Administrador';

  const filteredDepartments = useMemo(() => {
    const term = normalize(search);
    const matches = !term
      ? departamentos
      : departamentos.filter((department) => {
          const departmentMatch = normalize(department.nombre).includes(term);
          const subareaMatch = (department.subareas || []).some((subarea) =>
            normalize(subarea.nombre).includes(term)
          );

          return departmentMatch || subareaMatch;
        });

    return [...matches].sort((left, right) =>
      (left.nombre || '').localeCompare(right.nombre || '', 'es', {
        sensitivity: 'base',
      })
    );
  }, [departamentos, search]);

  const selectedDepartment = useMemo(() => (
    departamentos.find(
      (department) => department.id === selectedDepartmentId
    )
    || departamentos.find((department) => department.activo)
    || departamentos[0]
    || null
  ), [departamentos, selectedDepartmentId]);

  const effectiveSelectedDepartmentId = selectedDepartment?.id ?? null;

  const activeDepartmentCount = departamentos.filter(
    (department) => department.activo
  ).length;

  const activeSubareaCount = departamentos.reduce(
    (total, department) =>
      total + (department.subareas || []).filter((subarea) => subarea.activo).length,
    0
  );

  const closeModal = () => {
    if (!saving) {
      setModal(null);
    }
  };

  const openDepartmentCreate = () => {
    setModal({
      type: 'department-create',
      values: { nombre: '' },
    });
  };

  const openDepartmentEdit = (department) => {
    setModal({
      type: 'department-edit',
      item: department,
      values: { nombre: department.nombre },
    });
  };

  const openSubareaCreate = (department) => {
    setModal({
      type: 'subarea-create',
      department,
      values: { nombre: '' },
    });
  };

  const openSubareaEdit = (subarea) => {
    setModal({
      type: 'subarea-edit',
      item: subarea,
      values: { nombre: subarea.nombre },
    });
  };

  const setModalName = (value) => {
    setModal((current) => ({
      ...current,
      values: {
        ...current.values,
        nombre: value,
      },
    }));
  };

  const validateModalName = () => {
    const nombre = modal?.values?.nombre?.trim().replace(/\s+/g, ' ');

    if (!nombre) {
      showToast?.('Debe ingresar un nombre.', 'error');
      return null;
    }

    if (nombre.length > 100) {
      showToast?.('El nombre puede tener como máximo 100 caracteres.', 'error');
      return null;
    }

    if (modal.type.startsWith('department')) {
      const duplicated = departamentos.some(
        (department) =>
          department.id !== modal.item?.id &&
          normalize(department.nombre) === normalize(nombre)
      );

      if (duplicated) {
        showToast?.(`Ya existe el departamento "${nombre}".`, 'error');
        return null;
      }
    }

    if (modal.type.startsWith('subarea')) {
      const department = modal.department || selectedDepartment;
      const duplicated = (department?.subareas || []).some(
        (subarea) =>
          subarea.id !== modal.item?.id &&
          normalize(subarea.nombre) === normalize(nombre)
      );

      if (duplicated) {
        showToast?.(
          `Ya existe la subárea "${nombre}" dentro de ${department?.nombre || 'este departamento'}.`,
          'error'
        );
        return null;
      }
    }

    return nombre;
  };

  const submitModal = async (event) => {
    event.preventDefault();

    const nombre = validateModalName();
    if (!nombre) return;

    setSaving(true);

    try {
      if (modal.type === 'department-create') {
        const created = await createDepartamento({ nombre, activo: true });
        setSelectedDepartmentId(created.id);
        showToast?.('Departamento creado correctamente.', 'success');
      }

      if (modal.type === 'department-edit') {
        await updateDepartamento(modal.item.id, { nombre });
        showToast?.('Departamento actualizado correctamente.', 'success');
      }

      if (modal.type === 'subarea-create') {
        await createSubarea({
          departamento: modal.department.id,
          nombre,
          activo: true,
        });
        showToast?.('Subárea creada correctamente.', 'success');
      }

      if (modal.type === 'subarea-edit') {
        await updateSubarea(modal.item.id, { nombre });
        showToast?.('Subárea actualizada correctamente.', 'success');
      }

      setModal(null);
      await onRefresh?.();
    } catch (error) {
      showToast?.(getApiErrorMessage(error), 'error');
    } finally {
      setSaving(false);
    }
  };

  const toggleDepartment = async (department) => {
    const nextActive = !department.activo;
    const confirmed = await requestConfirmation?.({
      title: nextActive ? 'Activar departamento' : 'Desactivar departamento',
      message: nextActive
        ? `¿Deseas volver a activar "${department.nombre}"?`
        : `¿Deseas desactivar "${department.nombre}"? Los registros existentes conservarán su relación.`,
      confirmText: nextActive ? 'Activar' : 'Desactivar',
      danger: !nextActive,
    });

    if (confirmed === false) return;

    try {
      await updateDepartamento(department.id, { activo: nextActive });
      showToast?.(
        nextActive
          ? 'Departamento activado correctamente.'
          : 'Departamento desactivado correctamente.',
        'success'
      );
      await onRefresh?.();
    } catch (error) {
      showToast?.(getApiErrorMessage(error), 'error');
    }
  };

  const toggleSubarea = async (subarea) => {
    const nextActive = !subarea.activo;
    const confirmed = await requestConfirmation?.({
      title: nextActive ? 'Activar subárea' : 'Desactivar subárea',
      message: nextActive
        ? `¿Deseas volver a activar "${subarea.nombre}"?`
        : `¿Deseas desactivar "${subarea.nombre}"? Los usuarios existentes conservarán su relación.`,
      confirmText: nextActive ? 'Activar' : 'Desactivar',
      danger: !nextActive,
    });

    if (confirmed === false) return;

    try {
      await updateSubarea(subarea.id, { activo: nextActive });
      showToast?.(
        nextActive
          ? 'Subárea activada correctamente.'
          : 'Subárea desactivada correctamente.',
        'success'
      );
      await onRefresh?.();
    } catch (error) {
      showToast?.(getApiErrorMessage(error), 'error');
    }
  };

  const removeSubarea = async (subarea) => {
    const confirmed = await requestConfirmation?.({
      title: 'Eliminar subárea',
      message: `¿Deseas eliminar definitivamente "${subarea.nombre}"? Esta acción solo se permite si no tiene usuarios asociados.`,
      confirmText: 'Eliminar',
      danger: true,
    });

    if (confirmed === false) return;

    try {
      await deleteSubarea(subarea.id);
      showToast?.('Subárea eliminada correctamente.', 'success');
      await onRefresh?.();
    } catch (error) {
      showToast?.(getApiErrorMessage(error), 'error');
    }
  };

  const removeDepartment = async (department) => {
    const confirmed = await requestConfirmation?.({
      title: 'Eliminar departamento',
      message: `¿Deseas eliminar definitivamente "${department.nombre}"? Solo se puede eliminar si no tiene usuarios ni subáreas asociadas.`,
      confirmText: 'Eliminar',
      danger: true,
    });

    if (confirmed === false) return;

    try {
      await deleteDepartamento(department.id);
      showToast?.('Departamento eliminado correctamente.', 'success');
      setSelectedDepartmentId(null);
      await onRefresh?.();
    } catch (error) {
      showToast?.(getApiErrorMessage(error), 'error');
    }
  };

  const modalTitle = (() => {
    switch (modal?.type) {
      case 'department-create':
        return 'Nuevo Departamento';
      case 'department-edit':
        return 'Editar Departamento';
      case 'subarea-create':
        return `Nueva Subárea · ${modal.department?.nombre || ''}`;
      case 'subarea-edit':
        return 'Editar Subárea';
      default:
        return '';
    }
  })();

  const formContent = modal && (
    <div className="department-modal-field">
      <label htmlFor="department-name">
        {modal.type.startsWith('department') ? 'Nombre del Departamento' : 'Nombre de la Subárea'}
      </label>
      <input
        id="department-name"
        type="text"
        autoFocus
        maxLength={100}
        required
        value={modal.values.nombre}
        onChange={(event) => setModalName(event.target.value)}
        placeholder={
          modal.type.startsWith('department')
            ? 'Ej: Tecnología'
            : 'Ej: Infraestructura'
        }
      />
      <span>Las diferencias de mayúsculas, minúsculas o espacios no crean duplicados.</span>
    </div>
  );

  return (
    <section className="departments-page">
      <div className="departments-summary">
        <div className="departments-summary-copy">
          <span className="departments-eyebrow">Catálogo organizacional</span>
          <h2>Departamentos y Subáreas</h2>
          <p>
            Administra la estructura que posteriormente se utilizará en las fichas de usuarios.
          </p>
        </div>

        <div className="departments-stats">
          <div>
            <strong>{activeDepartmentCount}</strong>
            <span>Departamentos activos</span>
          </div>
          <div>
            <strong>{activeSubareaCount}</strong>
            <span>Subáreas activas</span>
          </div>
        </div>
      </div>

      <div className="departments-actions">
        <button
          type="button"
          className="departments-primary-action"
          onClick={openDepartmentCreate}
        >
          <Plus size={17} />
          Agregar Departamento
        </button>

        <label className="departments-search">
          <Search size={16} />
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar departamento o subárea..."
          />
        </label>
      </div>

      <div className="department-chip-list" aria-label="Departamentos">
        {filteredDepartments.map((department) => {
          const active = effectiveSelectedDepartmentId === department.id;
          const activeSubareas = (department.subareas || []).filter(
            (subarea) => subarea.activo
          ).length;

          return (
            <button
              key={department.id}
              type="button"
              aria-pressed={active}
              className={`department-chip ${active ? 'is-selected' : ''} ${
                !department.activo ? 'is-disabled' : ''
              }`}
              onClick={() => setSelectedDepartmentId(department.id)}
            >
              <span>{department.nombre}</span>
              <strong>{activeSubareas}</strong>
            </button>
          );
        })}
      </div>

      {!filteredDepartments.length && (
        <div className="departments-empty">
          No se encontraron departamentos o subáreas con esa búsqueda.
        </div>
      )}

      {selectedDepartment && (
        <div className="department-detail-panel">
          <div className="department-detail-header">
            <div className="department-detail-title">
              <div className="department-detail-icon">
                <Building2 size={20} />
              </div>
              <div>
                <span>Departamento seleccionado</span>
                <h3>{selectedDepartment.nombre}</h3>
                <p>
                  {selectedDepartment.activo ? 'Activo' : 'Inactivo'} ·{' '}
                  {(selectedDepartment.subareas || []).length}{' '}
                  {(selectedDepartment.subareas || []).length === 1 ? 'subárea' : 'subáreas'}
                </p>
              </div>
            </div>

            <div className="department-detail-actions">
              <button
                type="button"
                className="department-secondary-action"
                onClick={() => openDepartmentEdit(selectedDepartment)}
              >
                <Pencil size={15} />
                Editar
              </button>
              <button
                type="button"
                className={`department-secondary-action ${
                  selectedDepartment.activo ? 'is-danger' : 'is-success'
                }`}
                onClick={() => toggleDepartment(selectedDepartment)}
              >
                {selectedDepartment.activo ? <Power size={15} /> : <CheckCircle2 size={15} />}
                {selectedDepartment.activo ? 'Desactivar' : 'Activar'}
              </button>
              {canDelete && (
                <button
                  type="button"
                  className="department-secondary-action is-danger"
                  onClick={() => removeDepartment(selectedDepartment)}
                  title="Eliminar departamento definitivamente"
                >
                  <Trash2 size={15} />
                  Eliminar
                </button>
              )}
            </div>
          </div>

          <div className="subareas-section">
            <div className="subareas-heading">
              <div>
                <span className="departments-eyebrow">Subáreas</span>
                <h4>Estructura interna</h4>
              </div>

              <button
                type="button"
                className="department-add-subarea"
                onClick={() => openSubareaCreate(selectedDepartment)}
                disabled={!selectedDepartment.activo}
                title={
                  selectedDepartment.activo
                    ? 'Agregar subárea'
                    : 'Activa el departamento antes de agregar subáreas'
                }
              >
                <Plus size={16} />
                Agregar Subárea
              </button>
            </div>

            {(selectedDepartment.subareas || []).length ? (
              <div className="subarea-chip-grid">
                {[...(selectedDepartment.subareas || [])]
                  .sort((left, right) =>
                    (left.nombre || '').localeCompare(right.nombre || '', 'es', {
                      sensitivity: 'base',
                    })
                  )
                  .map((subarea) => (
                  <div
                    key={subarea.id}
                    className={`subarea-chip ${!subarea.activo ? 'is-disabled' : ''}`}
                  >
                    <div className="subarea-chip-name">
                      <Layers3 size={15} />
                      <span>{subarea.nombre}</span>
                    </div>

                    <div className="subarea-chip-actions">
                      <button
                        type="button"
                        onClick={() => openSubareaEdit(subarea)}
                        title="Editar subárea"
                        aria-label={`Editar ${subarea.nombre}`}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleSubarea(subarea)}
                        title={subarea.activo ? 'Desactivar subárea' : 'Activar subárea'}
                        aria-label={
                          subarea.activo
                            ? `Desactivar ${subarea.nombre}`
                            : `Activar ${subarea.nombre}`
                        }
                      >
                        {subarea.activo ? <Power size={14} /> : <CheckCircle2 size={14} />}
                      </button>
                      {canDelete && (
                        <button
                          type="button"
                          className="is-delete"
                          onClick={() => removeSubarea(subarea)}
                          title="Eliminar subárea definitivamente"
                          aria-label={`Eliminar ${subarea.nombre}`}
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                  ))}
              </div>
            ) : (
              <div className="subareas-empty">
                Este departamento todavía no tiene subáreas registradas.
              </div>
            )}
          </div>
        </div>
      )}

      {modal?.type?.endsWith('create') && (
        <CreateModal
          title={modalTitle}
          onClose={closeModal}
          onSubmit={submitModal}
        >
          {formContent}
        </CreateModal>
      )}

      {modal?.type?.endsWith('edit') && (
        <EditModal
          title={modalTitle}
          onClose={closeModal}
          onSubmit={submitModal}
        >
          {formContent}
        </EditModal>
      )}
    </section>
  );
}
