import { useMemo, useState } from 'react';
import PasswordInput from './PasswordInput';

export default function UsuarioEditForm({
  usuario,
  onChange,
  departments = [],
  availableIps,
}) {
  const [showPasswordGmail, setShowPasswordGmail] = useState(false);
  const [showPasswordVpn, setShowPasswordVpn] = useState(false);

  const selectedDepartmentId = usuario.departamento ? Number(usuario.departamento) : null;
  const selectedSubareaId = usuario.subarea ? Number(usuario.subarea) : null;

  const selectedDepartment = departments.find(
    (department) => Number(department.id) === selectedDepartmentId
  );

  const availableDepartments = useMemo(
    () =>
      departments.filter(
        (department) => department.activo || Number(department.id) === selectedDepartmentId
      ),
    [departments, selectedDepartmentId]
  );

  const availableSubareas = useMemo(
    () =>
      (selectedDepartment?.subareas || []).filter(
        (subarea) => subarea.activo || Number(subarea.id) === selectedSubareaId
      ),
    [selectedDepartment, selectedSubareaId]
  );

  const updateField = (field, value) => {
    onChange({
      ...usuario,
      [field]: value,
    });
  };

  const handleStatusChange = (value) => {
    const nextUsuario = {
      ...usuario,
      estado: value,
    };

    // Si había una selección pendiente y el usuario deja de estar ACTIVO,
    // la descartamos. La IP actual se conserva visualmente desde ip_actual;
    // BAJA será liberada automáticamente por el backend al guardar.
    if (value !== 'ACTIVO' && 'ip_seleccionada' in nextUsuario) {
      delete nextUsuario.ip_seleccionada;
    }

    onChange(nextUsuario);
  };

  const ipAssignmentDisabled = (usuario.estado || 'ACTIVO') !== 'ACTIVO';

  const handleDepartmentChange = (value) => {
    const departmentId = value ? Number(value) : null;

    onChange({
      ...usuario,
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
        <label style={labelStyle}>Estado del Usuario</label>
        <select
          value={usuario.estado || 'ACTIVO'}
          onChange={(e) => handleStatusChange(e.target.value)}
          style={inputStyle}
        >
          <option value="ACTIVO">Activo</option>
          <option value="LICENCIA">Licencia Médica</option>
          <option value="BAJA">Dar de Baja</option>
        </select>
      </div>

      <div>
        <label style={labelStyle}>Nombre Completo</label>
        <input
          type="text"
          value={usuario.nombre_completo || ''}
          maxLength={150}
          onChange={(e) => updateField('nombre_completo', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Departamento *</label>
        <select
          required
          value={usuario.departamento ?? ''}
          onChange={(e) => handleDepartmentChange(e.target.value)}
          style={inputStyle}
        >
          <option value="">Selecciona un Departamento...</option>
          {availableDepartments.map((department) => (
            <option key={department.id} value={department.id}>
              {department.nombre}{!department.activo ? ' (Inactivo)' : ''}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label style={labelStyle}>Subárea</label>
        <select
          value={usuario.subarea ?? ''}
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
              {subarea.nombre}{!subarea.activo ? ' (Inactiva)' : ''}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label style={labelStyle}>Cargo</label>
        <input
          type="text"
          value={usuario.cargo || ''}
          maxLength={100}
          onChange={(e) => updateField('cargo', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={{ ...labelStyle, color: '#0284c7' }}>Hostname</label>
        <input
          type="text"
          value={usuario.hostname || ''}
          maxLength={50}
          onChange={(e) => updateField('hostname', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Usuario de Red</label>
        <input
          type="text"
          value={usuario.usuario_red || ''}
          maxLength={50}
          onChange={(e) => updateField('usuario_red', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Correo Corp.</label>
        <input
          type="email"
          value={usuario.correo_corp || ''}
          maxLength={254}
          onChange={(e) => updateField('correo_corp', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Gmail</label>
        <input
          type="email"
          value={usuario.gmail || ''}
          maxLength={254}
          onChange={(e) => updateField('gmail', e.target.value)}
          style={inputStyle}
        />
      </div>

      <PasswordInput
        label="Contraseña Gmail"
        value={usuario.password_gmail}
        onChange={(value) => updateField('password_gmail', value)}
        visible={showPasswordGmail}
        onToggle={() => setShowPasswordGmail((prev) => !prev)}
      />

      <PasswordInput
        label="Contraseña VPN"
        value={usuario.password_vpn}
        onChange={(value) => updateField('password_vpn', value)}
        visible={showPasswordVpn}
        onToggle={() => setShowPasswordVpn((prev) => !prev)}
      />

      <div>
        <label style={{ ...labelStyle, color: '#16a34a' }}>
          Seleccionar IP Asignada
        </label>
        <select
          value={
            usuario.ip_seleccionada !== undefined
              ? usuario.ip_seleccionada ?? ''
              : usuario.ip_actual ?? ''
          }
          onChange={(e) =>
            updateField('ip_seleccionada', e.target.value || null)
          }
          disabled={ipAssignmentDisabled}
          style={{
            ...inputStyle,
            fontWeight: 'bold',
            color: ipAssignmentDisabled ? '#94a3b8' : '#15803d',
            backgroundColor: ipAssignmentDisabled ? '#f8fafc' : '#fff',
          }}
        >
          <option value="">Sin IP Asignada</option>
          {availableIps.map((ip) => (
            <option key={ip.id} value={ip.direccion_ip}>
              {ip.direccion_ip} ({ip.observacion || 'Libre'})
            </option>
          ))}
        </select>
        {ipAssignmentDisabled && (
          <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#64748b' }}>
            Las IP solo se pueden asignar o cambiar cuando el usuario está Activo.
          </div>
        )}
      </div>
    </>
  );
}
