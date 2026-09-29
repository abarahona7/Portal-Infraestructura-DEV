import { useMemo, useState } from 'react';
import PasswordInput from './PasswordInput';
import AvailableIpSelector from './AvailableIpSelector';

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
    // la descartamos. BAJA y LICENCIA liberan la IP en el backend al guardar.
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
          aria-label="Estado del usuario"
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
          aria-label="Nombre completo"
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
          aria-label="Departamento"
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
          aria-label="Subárea"
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

      <div><label style={labelStyle}>RUT</label><input aria-label="RUT" value={usuario.rut || ''} maxLength={12} placeholder="12345678-5" onChange={(e) => updateField('rut', e.target.value)} style={inputStyle} /></div>
      <div><label style={labelStyle}>Centro de costo</label><input aria-label="Centro de costo" value={usuario.centro_costo || ''} maxLength={50} onChange={(e) => updateField('centro_costo', e.target.value)} style={inputStyle} /></div>
      <div><label style={labelStyle}>Ubicación</label><input aria-label="Ubicación" value={usuario.ubicacion || ''} maxLength={100} onChange={(e) => updateField('ubicacion', e.target.value)} style={inputStyle} /></div>

      <div>
        <label style={labelStyle}>Cargo</label>
        <input
          aria-label="Cargo"
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
          aria-label="Hostname"
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
          aria-label="Usuario de red"
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
          aria-label="Correo corporativo"
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
          aria-label="Cuenta Gmail"
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

      <AvailableIpSelector
        selectedIp={
          usuario.ip_seleccionada !== undefined
            ? usuario.ip_seleccionada ?? ''
            : usuario.ip_actual ?? ''
        }
        availableIps={availableIps}
        disabled={ipAssignmentDisabled}
        onIpChange={(value) => updateField('ip_seleccionada', value)}
      />
    </>
  );
}
