import { useState } from 'react';
import PasswordInput from './PasswordInput';


export default function UsuarioEditForm({
  usuario,
  onChange,
  departments,
  availableIps,
}) {

  const [showPasswordGmail, setShowPasswordGmail] = useState(false);
  const [showPasswordVpn, setShowPasswordVpn] = useState(false);

  const updateField = (field, value) => {
    onChange({
      ...usuario,
      [field]: value
    });
  };

  const inputStyle = {
    width: '100%',
    padding: '0.6rem',
    borderRadius: '6px',
    border: '1px solid #cbd5e1',
    marginTop: '4px',
    boxSizing: 'border-box'
  };

  const labelStyle = {
    fontSize: '0.8rem',
    color: '#64748b',
    fontWeight: 'bold'
  };

  return (
    <>
      {/* Estado */}
      <div>
        <label style={labelStyle}>
          Estado del Usuario
        </label>

        <select
          value={usuario.estado || 'ACTIVO'}
          onChange={(e) =>
            updateField('estado', e.target.value)
          }
          style={inputStyle}
        >
          <option value="ACTIVO">
            Activo
          </option>

          <option value="LICENCIA">
            Licencia Médica
          </option>

          <option value="BAJA">
            Dar de Baja
          </option>
        </select>
      </div>

      {/* Nombre */}
      <div>
        <label style={labelStyle}>
          Nombre Completo
        </label>

        <input
          type="text"
          value={usuario.nombre_completo || ''}
          onChange={(e) =>
            updateField(
              'nombre_completo',
              e.target.value
            )
          }
          style={inputStyle}
        />
      </div>

      {/* Departamento */}
      <div>
        <label style={labelStyle}>
          Departamento / Área
        </label>

        <select
          value={usuario.dpto_area || ''}
          onChange={(e) =>
            updateField(
              'dpto_area',
              e.target.value
            )
          }
          style={inputStyle}
        >
          <option value="">
            Selecciona un área...
          </option>

          {departments.map((department, index) => (
            <option
              key={index}
              value={department}
            >
              {department}
            </option>
          ))}
        </select>
      </div>

      {/* Cargo */}
      <div>
        <label style={labelStyle}>
          Cargo
        </label>

        <input
          type="text"
          value={usuario.cargo || ''}
          onChange={(e) =>
            updateField(
              'cargo',
              e.target.value
            )
          }
          style={inputStyle}
        />
      </div>

      {/* Hostname */}
      <div>
        <label
          style={{
            ...labelStyle,
            color: '#0284c7'
          }}
        >
          Hostname
        </label>

        <input
          type="text"
          value={usuario.hostname || ''}
          onChange={(e) =>
            updateField(
              'hostname',
              e.target.value
            )
          }
          style={inputStyle}
        />
      </div>

      {/* Usuario de Red */}
      <div>
        <label style={labelStyle}>
          Usuario de Red
        </label>

        <input
          type="text"
          value={usuario.usuario_red || ''}
          onChange={(e) =>
            updateField(
              'usuario_red',
              e.target.value
            )
          }
          style={inputStyle}
        />
      </div>

      {/* Correo Corporativo */}
      <div>
        <label style={labelStyle}>
          Correo Corp.
        </label>

        <input
          type="email"
          value={usuario.correo_corp || ''}
          onChange={(e) =>
            updateField(
              'correo_corp',
              e.target.value
            )
          }
          style={inputStyle}
        />
      </div>

      {/* Gmail */}
      <div>
        <label style={labelStyle}>
          Gmail
        </label>

        <input
          type="email"
          value={usuario.gmail || ''}
          onChange={(e) =>
            updateField(
              'gmail',
              e.target.value
            )
          }
          style={inputStyle}
        />
      </div>

      {/* Contraseñas */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '0.5rem'
        }}
      >
        <PasswordInput
          label="Contraseña Gmail"
          value={usuario.password_gmail}
          onChange={(value) =>
            updateField('password_gmail', value)
          }
          visible={showPasswordGmail}
          onToggle={() =>
            setShowPasswordGmail((prev) => !prev)
          }
        />
      </div>

      {/* Contraseña VPN */}
      <PasswordInput
        label="Contraseña VPN"
        value={usuario.password_vpn}
        onChange={(value) =>
          updateField('password_vpn', value)
        }
        visible={showPasswordVpn}
        onToggle={() =>
          setShowPasswordVpn((prev) => !prev)
        }
      />

      {/* IP */}
      <div>
        <label
          style={{
            ...labelStyle,
            color: '#16a34a'
          }}
        >
          Seleccionar IP Asignada
        </label>

        <select
          value={
            usuario.ip_seleccionada !== undefined
              ? (usuario.ip_seleccionada ?? '')
              : (usuario.ip_actual ?? '')
          }
          onChange={(e) =>
            updateField(
              'ip_seleccionada',
              e.target.value || null
            )
          }
          style={{
            ...inputStyle,
            fontWeight: 'bold',
            color: '#15803d'
          }}
        >
          <option value="">
            Sin IP Asignada
          </option>

          {availableIps.map((ip) => (
            <option
              key={ip.id}
              value={ip.direccion_ip}
            >
              {ip.direccion_ip}
              {' '}
              ({ip.observacion || 'Libre'})
            </option>
          ))}
        </select>
      </div>
    </>
  );
}