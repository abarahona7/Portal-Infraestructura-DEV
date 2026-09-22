import { useState } from 'react';
import PasswordInput from '../../usuarios/components/PasswordInput';

export default function PCGenericoCreateForm({
  pc,
  onChange,
  departments = [],
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
          type="text"
          required
          value={pc.usuario_local || ''}
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
          type="text"
          required
          value={pc.hostname || ''}
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

      {/* Departamento */}
      <div>
        <label style={labelStyle}>
          Departamento / Área
        </label>

        <select
          value={pc.dpto_area || ''}
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

      {/* Marca + Modelo */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '0.5rem'
        }}
      >
        <div>
          <label style={labelStyle}>
            Marca
          </label>

          <input
            type="text"
            value={pc.marca || ''}
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
            type="text"
            value={pc.modelo || ''}
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
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '0.5rem'
        }}
      >
        <div>
          <label style={labelStyle}>
            N.º de Serie
          </label>

          <input
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