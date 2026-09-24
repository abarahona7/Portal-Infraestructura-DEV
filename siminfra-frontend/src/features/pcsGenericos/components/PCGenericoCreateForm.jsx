import { useState } from 'react';
import PasswordInput from '../../usuarios/components/PasswordInput';
import AvailableIpSelector from '../../usuarios/components/AvailableIpSelector';
import PCGenericoDepartmentFields from './PCGenericoDepartmentFields';

export default function PCGenericoCreateForm({
  pc,
  onChange,
  departments = [],
  availableIps = [],
}) {
  const [showPassword, setShowPassword] = useState(false);

  const updateField = (field, value) => {
    onChange({
      ...pc,
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
      {/* Usuario Local */}
      <div>
        <label style={labelStyle}>
          Usuario Local *
        </label>

        <input
          aria-label="Usuario local"
          type="text"
          required
          value={pc.usuario_local || ''}
          maxLength={150}
          onChange={(e) =>
            updateField(
              'usuario_local',
              e.target.value
            )
          }
          placeholder="Ej: AUDITORIA SEREMI 2"
          style={inputStyle}
        />
      </div>

      {/* Contraseña */}
      <PasswordInput
        label="Contraseña"
        value={pc.password}
        onChange={(value) =>
          updateField('password', value)
        }
        visible={showPassword}
        onToggle={() =>
          setShowPassword((prev) => !prev)
        }
      />

      {/* Hostname */}
      <div>
        <label
          style={{
            ...labelStyle,
            color: '#0284c7'
          }}
        >
          Hostname *
        </label>

        <input
          aria-label="Hostname"
          type="text"
          required
          value={pc.hostname || ''}
          maxLength={100}
          onChange={(e) =>
            updateField(
              'hostname',
              e.target.value
            )
          }
          placeholder="Ej: cl_audiseremi2"
          style={inputStyle}
        />
      </div>

      <PCGenericoDepartmentFields
        pc={pc}
        onChange={onChange}
        departments={departments}
      />

      <AvailableIpSelector
        selectedIp={pc.ip_seleccionada ?? ''}
        availableIps={availableIps}
        onIpChange={(value) => updateField('ip_seleccionada', value)}
      />

      {/* Marca + Modelo */}
      <div className="responsive-form-grid">
        <div>
          <label style={labelStyle}>
            Marca
          </label>

          <input
            aria-label="Marca"
            type="text"
            value={pc.marca || ''}
            maxLength={100}
            onChange={(e) =>
              updateField(
                'marca',
                e.target.value
              )
            }
            placeholder="Ej: HP"
            style={inputStyle}
          />
        </div>

        <div>
          <label style={labelStyle}>
            Modelo
          </label>

          <input
            aria-label="Modelo"
            type="text"
            value={pc.modelo || ''}
            maxLength={100}
            onChange={(e) =>
              updateField(
                'modelo',
                e.target.value
              )
            }
            placeholder="Ej: ProDesk 400 G6"
            style={inputStyle}
          />
        </div>
      </div>

      {/* Serie + Activo Fijo */}
      <div className="responsive-form-grid">
        <div>
          <label style={labelStyle}>
            N.º de Serie
          </label>

          <input
            aria-label="Número de serie"
            type="text"
            maxLength={20}
            value={pc.numero_serie || ''}
            onChange={(e) =>
              updateField(
                'numero_serie',
                e.target.value.slice(0, 20)
              )
            }
            placeholder="Máx. 20 caracteres"
            style={inputStyle}
          />
        </div>

        <div>
          <label style={labelStyle}>
            Activo Fijo
          </label>

          <input
            aria-label="Activo fijo"
            type="text"
            maxLength={12}
            value={pc.activo_fijo || ''}
            onChange={(e) => {
              const value = e.target.value
                .replace(/[^a-zA-Z0-9]/g, '')
                .slice(0, 12);

              updateField('activo_fijo', value);
            }}
            placeholder="Ej: 102401000300 o SINAF"
            style={inputStyle}
          />
        </div>
      </div>

      {/* ID TeamViewer */}
      <div>
        <label style={labelStyle}>
          ID TeamViewer
        </label>

        <input
          aria-label="ID TeamViewer"
          type="text"
          maxLength={20}
          value={pc.teamviewer_id || ''}
          onChange={(e) =>
            updateField(
              'teamviewer_id',
              e.target.value
            )
          }
          placeholder="Ej: 123 456 789"
          style={inputStyle}
        />
      </div>


      {/* Observaciones */}
      <div>
        <label style={labelStyle}>
          Observaciones
        </label>

        <textarea
          aria-label="Observaciones"
          value={pc.observaciones || ''}
          onChange={(e) =>
            updateField(
              'observaciones',
              e.target.value
            )
          }
          placeholder="Ej: BODEGA 37"
          rows={3}
          style={{
            ...inputStyle,
            resize: 'vertical',
            fontFamily: 'inherit'
          }}
        />
      </div>
    </>
  );
}
