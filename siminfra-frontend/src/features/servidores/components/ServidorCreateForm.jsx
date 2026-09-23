export default function ServidorCreateForm({
  servidor,
  onChange,
  availableIps = [],
}) {
  const updateField = (field, value) => {
    onChange({ ...servidor, [field]: value });
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

  const fieldStyle = { marginBottom: '1rem' };

  return (
    <>
      <div style={fieldStyle}>
        <label style={labelStyle}>Dirección IP *</label>
        <select
          required
          value={servidor.ip || ''}
          onChange={(event) => updateField('ip', event.target.value)}
          style={{ ...inputStyle, fontFamily: 'monospace' }}
        >
          <option value="">Selecciona una IP disponible...</option>
          {availableIps.map((ip) => (
            <option key={ip.id} value={ip.direccion_ip}>
              {ip.direccion_ip}
            </option>
          ))}
        </select>
        <small style={{ color: '#64748b' }}>
          Solo se muestran direcciones libres del segmento 172.23.1.0/24.
        </small>
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle}>Hostname *</label>
        <input
          type="text"
          required
          maxLength={100}
          value={servidor.hostname || ''}
          onChange={(event) => updateField('hostname', event.target.value)}
          placeholder="Ej: SRV-SQL-01"
          style={inputStyle}
        />
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle}>Descripción</label>
        <textarea
          value={servidor.descripcion || ''}
          onChange={(event) => updateField('descripcion', event.target.value)}
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
