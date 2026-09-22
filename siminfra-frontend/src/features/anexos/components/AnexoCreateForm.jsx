export default function AnexoCreateForm({
  anexo,
  onChange,
  usuarios,
}) {
  const updateField = (field, value) => {
    onChange({
      ...anexo,
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

  const estadoAutomatico = anexo.usuario
    ? 'ASIGNADO'
    : 'DISPONIBLE';

  const usuariosDisponibles = usuarios.filter(
    (usuario) => usuario.estado !== 'BAJA'
  );

  return (
    <>
      {/* Número de Anexo */}
      <div style={{ marginBottom: '1rem' }}>
        <label
          style={{
            display: 'block',
            marginBottom: '0.4rem',
            fontSize: '0.8rem',
            fontWeight: '600',
            color: '#475569'
          }}
        >
          Número de Anexo *
        </label>

        <input
          type="text"
          inputMode="numeric"
          required
          maxLength={10}
          value={anexo.numero_anexo || ''}
          onChange={(e) => {
            const value = e.target.value.replace(
              /\D/g,
              ''
            );

            updateField(
              'numero_anexo',
              value
            );
          }}
          placeholder="Ej: 3055"
          style={{
            width: '100%',
            padding: '0.65rem 0.75rem',
            borderRadius: '6px',
            border: '1px solid #cbd5e1',
            outline: 'none',
            boxSizing: 'border-box',
            fontSize: '0.9rem'
          }}
        />
      </div>

      {/* Número Exterior */}
      <div style={{ marginBottom: '1rem' }}>
        <label
          style={{
            display: 'block',
            marginBottom: '0.4rem',
            fontSize: '0.8rem',
            fontWeight: '600',
            color: '#475569'
          }}
        >
          Número Exterior
        </label>

        <input
          type="text"
          inputMode="tel"
          maxLength={12}
          value={anexo.exterior || ''}
          onChange={(e) => {
            let value = e.target.value;

            // Solo números y +
            value = value.replace(/[^\d+]/g, '');

            // El + solo puede estar al inicio
            value = value.replace(/(?!^)\+/g, '');

            // Máximo 12 caracteres
            value = value.slice(0, 12);

            updateField(
              'exterior',
              value
            );
          }}
          placeholder="Ej: +56221234567"
          style={{
            width: '100%',
            padding: '0.65rem 0.75rem',
            borderRadius: '6px',
            border: '1px solid #cbd5e1',
            outline: 'none',
            boxSizing: 'border-box',
            fontSize: '0.9rem'
          }}
        />
      </div>

      {/* Usuario */}
      <div>
        <label
          style={{
            ...labelStyle,
            color: '#2563eb'
          }}
        >
          Asignado a (Usuario)
        </label>

        <select
          value={anexo.usuario || ''}
          onChange={(e) =>
            updateField(
              'usuario',
              e.target.value || null
            )
          }
          style={inputStyle}
        >
          <option value="">
            Sin Asignar (Disponible)
          </option>

          {usuariosDisponibles.map((usuario) => (
            <option
              key={usuario.id}
              value={usuario.id}
            >
              {usuario.nombre_completo}
              {' '}
              ({usuario.usuario_red})
            </option>
          ))}
        </select>
      </div>

      {/* Estado automático */}
      <div>
        <label style={labelStyle}>
          Estado
        </label>

        <input
          type="text"
          value={estadoAutomatico}
          readOnly
          style={{
            ...inputStyle,
            backgroundColor: '#f8fafc',
            color:
              estadoAutomatico === 'ASIGNADO'
                ? '#2563eb'
                : '#15803d',
            fontWeight: 'bold',
            cursor: 'not-allowed'
          }}
        />
      </div>

      {/* Observaciones */}
      <div>
        <label style={labelStyle}>
          Observaciones
        </label>

        <input
          type="text"
          placeholder="Ej: Anexo recepción principal"
          value={anexo.observaciones || ''}
          onChange={(e) =>
            updateField(
              'observaciones',
              e.target.value
            )
          }
          style={inputStyle}
        />
      </div>
    </>
  );
}