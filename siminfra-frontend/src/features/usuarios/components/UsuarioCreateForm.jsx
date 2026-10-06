import { useMemo, useState } from 'react';
import PasswordInput from './PasswordInput';
import AvailableIpSelector from './AvailableIpSelector';
import { normalizeCorporateLineInput } from '../../../utils/userCorporateLines';

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

  const handleStatusChange = (value) => {
    onChange({
      ...usuario,
      estado: value,
      ...(value === 'ACTIVO' ? {} : { ip_seleccionada: null }),
      ...(value === 'BAJA' ? { celular: '' } : {}),
    });
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
        <label style={labelStyle}>Nombre Completo *</label>
        <input
          aria-label="Nombre completo"
          type="text"
          required
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
              {department.nombre}
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
              {subarea.nombre}
            </option>
          ))}
        </select>
      </div>

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
          placeholder="Ej: LAPTOP-FIN-01"
          value={usuario.hostname || ''}
          maxLength={50}
          onChange={(e) => updateField('hostname', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Usuario de Red *</label>
        <input
          aria-label="Usuario de red"
          type="text"
          required
          value={usuario.usuario_red || ''}
          maxLength={50}
          onChange={(e) => updateField('usuario_red', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Correo Corp. *</label>
        <input
          aria-label="Correo corporativo"
          type="email"
          required
          value={usuario.correo_corp || ''}
          maxLength={254}
          onChange={(e) => updateField('correo_corp', e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>Línea móvil corporativa</label>
        <input
          aria-label="Línea móvil corporativa"
          type="tel"
          inputMode="tel"
          maxLength={12}
          pattern="[+][0-9]{11}"
          placeholder="+56912345678"
          value={usuario.celular || ''}
          disabled={usuario.estado === 'BAJA'}
          onChange={(e) => updateField('celular', normalizeCorporateLineInput(e.target.value))}
          style={inputStyle}
        />
        <small>Opcional. Puedes registrar la línea aunque no conozcas el dispositivo.</small>
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
        selectedIp={usuario.ip_seleccionada ?? ''}
        availableIps={availableIps}
        disabled={ipAssignmentDisabled}
        onIpChange={(value) => updateField('ip_seleccionada', value)}
      />
    </>
  );
}
