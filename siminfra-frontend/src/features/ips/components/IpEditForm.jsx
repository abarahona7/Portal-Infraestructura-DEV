import { getIpSegment } from '../../../utils/ipHelpers';

export default function IpEditForm({
  ip,
  onChange,
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

  const isUserAssigned = Boolean(
    ip.usuario || ip.tipo_asignacion === 'USUARIO'
  );
  const isModuleManaged = ['SERVIDOR', 'PC_GENERICO'].includes(
    ip.tipo_asignacion
  );
  const isOtherAssigned = Boolean(ip.asignado_otro?.trim());
  const isReserved = Boolean(
    ip.tipo_asignacion || isUserAssigned || isOtherAssigned
  );
  const segment = getIpSegment(ip.direccion_ip || '');

  return (
    <>
      <div>
        <label style={labelStyle}>
          Dirección IP * (debe pertenecer a un segmento administrado)
        </label>

        <input
          aria-label="Dirección IP"
          type="text"
          required
          maxLength={15}
          value={ip.direccion_ip || ''}
          onChange={(e) => onIpChange(e.target.value)}
          disabled={isUserAssigned || isModuleManaged}
          style={inputStyle}
        />

        {ip.direccion_ip && segment && (
          <small style={{ color: '#64748b' }}>
            Segmento: {segment.label} · {segment.network}
          </small>
        )}
      </div>

      <div>
        <label style={labelStyle}>
          Estado de la IP
        </label>

        <div
          style={{
            ...inputStyle,
            backgroundColor: '#f8fafc',
            color: isReserved ? '#b45309' : '#15803d',
            fontWeight: 700,
          }}
        >
          {isReserved ? 'Reservada' : 'Libre'} · automático
        </div>
      </div>

      {isUserAssigned && (
        <div>
          <label style={{ ...labelStyle, color: '#2563eb' }}>
            Usuario asignado
          </label>

          <div
            style={{
              ...inputStyle,
              backgroundColor: '#eff6ff',
              color: '#1d4ed8',
              fontWeight: 700,
            }}
          >
            {ip.usuario_nombre || 'Usuario asignado'}
          </div>

          <small style={{ color: '#64748b' }}>
            Para cambiar o liberar esta asignación debes editar la ficha del usuario.
          </small>
        </div>
      )}

      {isModuleManaged && (
        <div>
          <label style={{ ...labelStyle, color: '#2563eb' }}>
            Asignación administrada
          </label>

          <div
            style={{
              ...inputStyle,
              backgroundColor: '#eff6ff',
              color: '#1d4ed8',
              fontWeight: 700,
            }}
          >
            {ip.asignado_a || ip.asignado_otro || 'Registro asignado'}
          </div>

          <small style={{ color: '#64748b' }}>
            Para cambiar o liberar esta IP debes editar el servidor o PC genérico relacionado.
          </small>
        </div>
      )}

      {!isUserAssigned && !isModuleManaged && (
        <div>
          <label
            style={{
              ...labelStyle,
              color: '#0284c7',
            }}
          >
            Asignado a otro artefacto o servicio
          </label>

          <input
            aria-label="Asignado a otro artefacto o servicio"
            type="text"
            maxLength={150}
            placeholder="Ej: Servidor DB / CCTV Piso 1 / Impresora Finanzas"
            value={ip.asignado_otro || ''}
            onChange={(e) => updateField('asignado_otro', e.target.value)}
            style={inputStyle}
          />

          <small style={{ color: '#64748b' }}>
            Las IP de usuarios se asignan únicamente desde el módulo Usuarios.
          </small>
        </div>
      )}

      <div>
        <label style={labelStyle}>
          Observaciones
        </label>

        <input
          aria-label="Observaciones"
          type="text"
          maxLength={255}
          value={ip.observacion || ''}
          onChange={(e) => updateField('observacion', e.target.value)}
          style={inputStyle}
        />
      </div>
    </>
  );
}
