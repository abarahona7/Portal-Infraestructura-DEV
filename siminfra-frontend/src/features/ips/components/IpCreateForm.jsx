import { getIpSegment } from '../../../utils/ipHelpers';

export default function IpCreateForm({
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

  const isOtherAssigned = Boolean(ip.asignado_otro?.trim());
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
          placeholder="Ej: 172.23.1.50"
          maxLength={15}
          value={ip.direccion_ip || ''}
          onChange={(e) => onIpChange(e.target.value)}
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
            color: isOtherAssigned ? '#b45309' : '#15803d',
            fontWeight: 700,
          }}
        >
          {isOtherAssigned ? 'Reservada' : 'Libre'} · automático
        </div>
      </div>

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

      <div>
        <label style={labelStyle}>
          Observaciones
        </label>

        <input
          aria-label="Observaciones"
          type="text"
          maxLength={255}
          placeholder="Ej: Punto de red sector recepción"
          value={ip.observacion || ''}
          onChange={(e) => updateField('observacion', e.target.value)}
          style={inputStyle}
        />
      </div>
    </>
  );
}
