import { useMemo, useState } from 'react';
import PasswordInput from './PasswordInput';

export default function UsuarioCreateForm({
  usuario,
  onChange,
  departments = [],
  availableIps,
}) {
  const [showPasswordGmail, setShowPasswordGmail] = useState(false);
  const [showPasswordVpn, setShowPasswordVpn] = useState(false);

  const selectedDepartmentId = usuario.departamento ? Number(usuario.departamento) : null;

  const selectedDepartment = departments.find(
    (department) => Number(department.id) === selectedDepartmentId
  );

  const availableDepartments = useMemo(
    () => departments.filter((department) => department.activo),
    [departments]
  );

  const availableSubareas = useMemo(
    () => (selectedDepartment?.subareas || []).filter((subarea) => subarea.activo),
    [selectedDepartment]
  );

  const updateField = (field, value) => {
    onChange({
      ...usuario,
      [field]: value,
    });
  };

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
          onChange={(e) => updateField('estado', e.target.value)}
          style={inputStyle}
        >
          <option value="ACTIVO">Activo</option>
          <option value="LICENCIA">Licencia Médica</option>
          <option value="BAJA">Dar de Baja</option>
        </select>
      </div>

      <div>
        <label style={labelStyle}>Nombre Completo *</label>
        <input
          type="text"
          required
          value={usuario.nombre_completo || ''}
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
              {department.nombre}
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
              {subarea.nombre}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label style={labelStyle}>Cargo</label>
        <input
          type="text"
          value={usuario.cargo || ''}
          onChange={(e) => updateField('cargo', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={{ ...labelStyle, color: '#0284c7' }}>Hostname</label>
        <input
          type="text"
          placeholder="Ej: LAPTOP-FIN-01"
          value={usuario.hostname || ''}
          onChange={(e) => updateField('hostname', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Usuario de Red *</label>
        <input
          type="text"
          required
          value={usuario.usuario_red || ''}
          onChange={(e) => updateField('usuario_red', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Correo Corp. *</label>
        <input
          type="email"
          required
          value={usuario.correo_corp || ''}
          onChange={(e) => updateField('correo_corp', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Gmail</label>
        <input
          type="email"
          value={usuario.gmail || ''}
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
          Seleccionar IP Disponible
        </label>
        <select
          value={usuario.ip_seleccionada ?? ''}
          onChange={(e) =>
            updateField('ip_seleccionada', e.target.value || null)
          }
          style={{ ...inputStyle, fontWeight: 'bold', color: '#15803d' }}
        >
          <option value="">Sin IP Asignada</option>
          {availableIps.map((ip) => (
            <option key={ip.id} value={ip.direccion_ip}>
              {ip.direccion_ip} ({ip.observacion || 'Libre'})
            </option>
          ))}
        </select>
      </div>
    </>
  );
}
