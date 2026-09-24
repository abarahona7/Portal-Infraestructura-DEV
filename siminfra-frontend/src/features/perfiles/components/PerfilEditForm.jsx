import { useMemo } from 'react';

export default function PerfilEditForm({
  perfil,
  onChange,
  departments = [],
}) {
  const selectedDepartmentId = perfil.departamento
    ? Number(perfil.departamento)
    : null;

  const selectedDepartment = departments.find(
    (department) => Number(department.id) === selectedDepartmentId
  );

  const availableDepartments = useMemo(() => {
    return departments.filter(
      (department) => department.activo || Number(department.id) === selectedDepartmentId
    );
  }, [departments, selectedDepartmentId]);

  const availableSubareas = useMemo(() => {
    const currentSubareaId = perfil.subarea ? Number(perfil.subarea) : null;
    return (selectedDepartment?.subareas || []).filter(
      (subarea) => subarea.activo || Number(subarea.id) === currentSubareaId
    );
  }, [selectedDepartment, perfil.subarea]);

  const updateField = (field, value) => {
    onChange({
      ...perfil,
      [field]: value,
    });
  };

  const handleDepartmentChange = (value) => {
    const departmentId = value ? Number(value) : null;

    onChange({
      ...perfil,
      departamento: departmentId,
      subarea: null,
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
    <>
      <div>
        <label style={labelStyle}>Estado</label>
        <select
          aria-label="Estado del perfil"
          value={perfil.estado || 'ACTIVO'}
          onChange={(e) => updateField('estado', e.target.value)}
          style={inputStyle}
        >
          <option value="ACTIVO">Activo</option>
          <option value="INACTIVO">Inactivo</option>
        </select>
      </div>

      <div>
        <label style={labelStyle}>Nombre / Perfil *</label>
        <input
          aria-label="Nombre o perfil"
          type="text"
          required
          value={perfil.nombre || ''}
          maxLength={150}
          onChange={(e) => updateField('nombre', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Usuario *</label>
        <input
          aria-label="Usuario del perfil"
          type="text"
          required
          value={perfil.usuario || ''}
          maxLength={100}
          onChange={(e) => updateField('usuario', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Nueva contraseña</label>
        <input
          aria-label="Nueva contraseña"
          type="password"
          value={perfil.password || ''}
          onChange={(e) => updateField('password', e.target.value)}
          placeholder="Déjalo vacío para conservar la actual"
          autoComplete="new-password"
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Tipo Cuenta</label>
        <select
          aria-label="Tipo de cuenta"
          value={perfil.tipo || 'On Premise'}
          onChange={(e) => updateField('tipo', e.target.value)}
          style={{
            ...inputStyle,
            backgroundColor: perfil.tipo === 'O365' ? '#eff6ff' : '#f8fafc',
            fontWeight: 'bold',
            color: perfil.tipo === 'O365' ? '#1d4ed8' : '#334155',
          }}
        >
          <option value="On Premise">On Premise</option>
          <option value="O365">O365</option>
        </select>
      </div>

      <div>
        <label style={labelStyle}>Correo Asignado</label>
        <input
          aria-label="Correo asignado"
          type="email"
          value={perfil.correo || ''}
          maxLength={254}
          onChange={(e) => updateField('correo', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Departamento *</label>
        <select
          aria-label="Departamento"
          required
          value={perfil.departamento ?? ''}
          onChange={(e) => handleDepartmentChange(e.target.value)}
          style={inputStyle}
        >
          <option value="">Selecciona un Departamento...</option>
          {availableDepartments.map((department) => (
            <option key={department.id} value={department.id}>
              {department.nombre}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label style={labelStyle}>Subárea</label>
        <select
          aria-label="Subárea"
          value={perfil.subarea ?? ''}
          onChange={(e) =>
            updateField('subarea', e.target.value ? Number(e.target.value) : null)
          }
          disabled={!selectedDepartmentId}
          style={{
            ...inputStyle,
            backgroundColor: selectedDepartmentId ? '#fff' : '#f8fafc',
          }}
        >
          <option value="">
            {selectedDepartmentId
              ? 'Selecciona una Subárea...'
              : 'Selecciona primero un Departamento'}
          </option>
          {availableSubareas.map((subarea) => (
            <option key={subarea.id} value={subarea.id}>
              {subarea.nombre}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label style={labelStyle}>Observaciones</label>
        <textarea
          aria-label="Observaciones"
          value={perfil.observaciones || ''}
          onChange={(e) => updateField('observaciones', e.target.value)}
          placeholder="Ej: Cuenta utilizada para soporte, sistema interno, acceso compartido, etc."
          rows={3}
          style={{ ...inputStyle, resize: 'vertical' }}
        />
      </div>
    </>
  );
}
