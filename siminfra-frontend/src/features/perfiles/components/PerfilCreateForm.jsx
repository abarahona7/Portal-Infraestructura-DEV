export default function PerfilCreateForm({
  perfil,
  onChange,
  departments,
}) {
  const updateField = (field, value) => {
    onChange({
      ...perfil,
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
      <div>
        <label style={labelStyle}>
          Nombre / Perfil *
        </label>

        <input
          type="text"
          required
          value={perfil.nombre || ''}
          onChange={(e) =>
            updateField('nombre', e.target.value)
          }
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>
          Usuario *
        </label>

        <input
          type="text"
          required
          value={perfil.usuario || ''}
          onChange={(e) =>
            updateField('usuario', e.target.value)
          }
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>
          Contraseña
        </label>

        <input
          type="text"
          value={perfil.password || ''}
          onChange={(e) =>
            updateField('password', e.target.value)
          }
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>
          Tipo Cuenta
        </label>

        <select
          value={perfil.tipo || 'On Premise'}
          onChange={(e) =>
            updateField('tipo', e.target.value)
          }
          style={{
            ...inputStyle,
            backgroundColor:
              perfil.tipo === 'O365'
                ? '#eff6ff'
                : '#f8fafc',
            fontWeight: 'bold',
            color:
              perfil.tipo === 'O365'
                ? '#1d4ed8'
                : '#334155'
          }}
        >
          <option value="On Premise">
            On Premise
          </option>

          <option value="O365">
            O365
          </option>
        </select>
      </div>

      <div>
        <label style={labelStyle}>
          Correo Asignado
        </label>

        <input
          type="email"
          value={perfil.correo || ''}
          onChange={(e) =>
            updateField('correo', e.target.value)
          }
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>
          Departamento / Área
        </label>

        <select
          value={perfil.dpto_area || ''}
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

      <div>
        <label style={labelStyle}>
          Observaciones
        </label>

        <textarea
          value={perfil.observaciones || ''}
          onChange={(e) =>
            updateField(
              'observaciones',
              e.target.value
            )
          }
          placeholder="Ej: Cuenta utilizada para soporte, sistema interno, acceso compartido, etc."
          rows={3}
          style={{
            ...inputStyle,
            resize: 'vertical'
          }}
        />
      </div>
    </>
  );
}