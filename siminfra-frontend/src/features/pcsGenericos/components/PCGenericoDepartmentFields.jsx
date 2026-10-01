import { useMemo } from 'react';


export default function PCGenericoDepartmentFields({
  pc,
  onChange,
  departments = [],
  preserveCurrentInactive = false,
}) {
  const selectedDepartmentId = pc.departamento
    ? Number(pc.departamento)
    : null;
  const selectedSubareaId = pc.subarea ? Number(pc.subarea) : null;

  const visibleDepartments = useMemo(
    () => departments.filter(
      (department) => department.activo
        || (preserveCurrentInactive && Number(department.id) === selectedDepartmentId)
    ),
    [departments, preserveCurrentInactive, selectedDepartmentId]
  );

  const selectedDepartment = departments.find(
    (department) => Number(department.id) === selectedDepartmentId
  );
  const visibleSubareas = useMemo(
    () => (selectedDepartment?.subareas || []).filter(
      (subarea) => subarea.activo
        || (preserveCurrentInactive && Number(subarea.id) === selectedSubareaId)
    ),
    [preserveCurrentInactive, selectedDepartment, selectedSubareaId]
  );

  const updateDepartment = (value) => {
    const departmentId = value ? Number(value) : null;
    onChange({
      ...pc,
      departamento: departmentId,
      subarea: null,
      dpto_area: '',
    });
  };

  const updateSubarea = (value) => {
    onChange({
      ...pc,
      subarea: value ? Number(value) : null,
      dpto_area: '',
    });
  };

  const inputStyle = {
    width: '100%',
    padding: '0.6rem',
    borderRadius: '6px',
    border: '1px solid #cbd5e1',
    marginTop: '4px',
    boxSizing: 'border-box',
  };
  const labelStyle = {
    fontSize: '0.8rem',
    color: '#64748b',
    fontWeight: 'bold',
  };

  return (
    <div className="responsive-form-grid">
      <div>
        <label style={labelStyle}>
          Departamento *
        </label>

        <select
          aria-label="Departamento"
          required
          value={pc.departamento ?? ''}
          onChange={(event) => updateDepartment(event.target.value)}
          style={inputStyle}
        >
          <option value="">Selecciona un departamento...</option>
          {visibleDepartments.map((department) => (
            <option key={department.id} value={department.id}>
              {department.nombre}{!department.activo ? ' (Inactivo)' : ''}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label style={labelStyle}>
          Área
        </label>

        <select
          aria-label="Área"
          value={pc.subarea ?? ''}
          disabled={!selectedDepartmentId}
          onChange={(event) => updateSubarea(event.target.value)}
          style={inputStyle}
        >
          <option value="">
            {selectedDepartmentId ? 'Sin área' : 'Selecciona un departamento primero'}
          </option>
          {visibleSubareas.map((subarea) => (
            <option key={subarea.id} value={subarea.id}>
              {subarea.nombre}{!subarea.activo ? ' (Inactiva)' : ''}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
