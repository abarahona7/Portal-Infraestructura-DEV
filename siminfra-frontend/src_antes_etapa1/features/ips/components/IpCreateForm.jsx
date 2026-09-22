export default function IpCreateForm({
  ip,
  onChange,
  usuarios,
  onIpChange,
}) {
  const updateField = (field, value) => {
    onChange({
      ...ip,
      [field]: value,
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

  const isUserAssigned = Boolean(ip.usuario);
  const isOtherAssigned = Boolean(ip.asignado_otro?.trim());

  const usuariosAsignables = usuarios.filter(
    (usuario) => usuario.estado === 'ACTIVO'
  );

  return (
    <>
      <div>
        <label style={labelStyle}>
          Dirección IP * (Solo números y puntos, máx. 15 caracteres)
        </label>

        <input
          type="text"
          required
          placeholder="Ej: 192.168.1.50"
          maxLength={15}
          value={ip.direccion_ip || ''}
          onChange={(e) => onIpChange(e.target.value)}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={labelStyle}>
          Estado de la IP *
        </label>

        {isUserAssigned ? (
          <div
            style={{
              ...inputStyle,
              backgroundColor: '#fee2e2',
              color: '#b91c1c',
              fontWeight: 700,
            }}
          >
            Reservada automáticamente al usuario
          </div>
        ) : (
          <select
            value={isOtherAssigned ? 'RESERVADA' : (ip.estado || 'LIBRE')}
            onChange={(e) => updateField('estado', e.target.value)}
            disabled={isOtherAssigned}
            style={{
              ...inputStyle,
              backgroundColor: isOtherAssigned ? '#f8fafc' : '#fff',
              cursor: isOtherAssigned ? 'not-allowed' : 'pointer',
            }}
          >
            <option value="LIBRE">Libre</option>
            <option value="RESERVADA">Reservada</option>
          </select>
        )}
      </div>

      <div>
        <label
          style={{
            ...labelStyle,
            color: '#2563eb',
          }}
        >
          Asignado a (Usuario)
        </label>

        <select
          value={ip.usuario || ''}
          onChange={(e) => {
            const usuarioId = e.target.value || null;

            onChange({
              ...ip,
              usuario: usuarioId,
              asignado_otro: '',
              estado: usuarioId ? 'RESERVADA' : 'LIBRE',
            });
          }}
          style={inputStyle}
        >
          <option value="">Sin Asignar (Ninguno)</option>

          {usuariosAsignables.map((usuario) => (
            <option key={usuario.id} value={usuario.id}>
              {usuario.nombre_completo} ({usuario.usuario_red})
            </option>
          ))}
        </select>
      </div>

      {!ip.usuario && (
        <div>
          <label
            style={{
              ...labelStyle,
              color: '#0284c7',
            }}
          >
            Otros (Servidor, CCTV, Impresora, etc.)
          </label>

          <input
            type="text"
            placeholder="Ej: Servidor DB / CCTV Piso 1"
            value={ip.asignado_otro || ''}
            onChange={(e) => {
              const value = e.target.value;

              onChange({
                ...ip,
                asignado_otro: value,
                estado: value.trim() ? 'RESERVADA' : 'LIBRE',
              });
            }}
            style={inputStyle}
          />
        </div>
      )}

      <div>
        <label style={labelStyle}>
          Observaciones
        </label>

        <input
          type="text"
          placeholder="Ej: Reservada para Impresora Piso 2"
          value={ip.observacion || ''}
          onChange={(e) => updateField('observacion', e.target.value)}
          style={inputStyle}
        />
      </div>
    </>
  );
}
