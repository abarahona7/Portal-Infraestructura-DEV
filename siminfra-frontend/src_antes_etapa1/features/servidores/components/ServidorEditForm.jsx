export default function ServidorEditForm({
  servidor,
  onChange,
}) {
  const updateField = (field, value) => {
    onChange({
      ...servidor,
      [field]: value,
    });
  };

  const inputStyle = {
    width: '100%',
    padding: '0.65rem',
    borderRadius: '7px',
    border: '1px solid #cbd5e1',
    marginTop: '4px',
    boxSizing: 'border-box',
    fontSize: '0.9rem',
  };

  const labelStyle = {
    display: 'block',
    fontSize: '0.8rem',
    color: '#475569',
    fontWeight: '700',
  };

  const fieldStyle = {
    marginBottom: '1rem',
  };

  return (
    <>
      {/* IP */}
      <div style={fieldStyle}>
        <label style={labelStyle}>
          Dirección IP *
        </label>

        <input
          type="text"
          inputMode="decimal"
          required
          maxLength={15}
          value={servidor.ip || ''}
          onChange={(e) => {
            const value = e.target.value.replace(
              /[^0-9.]/g,
              ''
            );

            const partes = value.split('.');

            // Máximo 4 bloques
            if (partes.length > 4) {
              return;
            }

            // Máximo 3 números por bloque
            if (
              partes.some(
                (parte) => parte.length > 3
              )
            ) {
              return;
            }

            // Cada bloque entre 0 y 255
            if (
              partes.some(
                (parte) =>
                  parte !== '' &&
                  Number(parte) > 255
              )
            ) {
              return;
            }

            updateField(
              'ip',
              value
            );
          }}
          placeholder="Ej: 172.23.10.15"
          style={{
            ...inputStyle,
            fontFamily: 'monospace',
          }}
        />
      </div>

      {/* HOSTNAME */}
      <div style={fieldStyle}>
        <label style={labelStyle}>
          Hostname *
        </label>

        <input
          type="text"
          required
          maxLength={100}
          value={servidor.hostname || ''}
          onChange={(e) =>
            updateField(
              'hostname',
              e.target.value
            )
          }
          placeholder="Ej: SRV-SQL-01"
          style={inputStyle}
        />
      </div>

      {/* DESCRIPCIÓN */}
      <div style={fieldStyle}>
        <label style={labelStyle}>
          Descripción
        </label>

        <textarea
          value={servidor.descripcion || ''}
          onChange={(e) =>
            updateField(
              'descripcion',
              e.target.value
            )
          }
          placeholder="Ej: Servidor SQL de producción"
          rows={4}
          style={{
            ...inputStyle,
            resize: 'vertical',
            minHeight: '100px',
            fontFamily: 'inherit',
          }}
        />
      </div>
    </>
  );
}