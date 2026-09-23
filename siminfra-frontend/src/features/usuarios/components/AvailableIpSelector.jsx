import { useMemo, useState } from 'react';

import {
  filterIpsBySegment,
  getIpSegment,
  IP_SEGMENTS,
} from '../../../utils/ipHelpers';


export default function AvailableIpSelector({
  selectedIp,
  availableIps = [],
  disabled = false,
  onIpChange,
}) {
  const [selectedSegment, setSelectedSegment] = useState(
    () => getIpSegment(selectedIp || '')?.id || ''
  );

  const segmentIps = useMemo(
    () => filterIpsBySegment(availableIps, selectedSegment),
    [availableIps, selectedSegment]
  );

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
    color: '#16a34a',
    fontWeight: 'bold',
  };

  const handleSegmentChange = (value) => {
    setSelectedSegment(value);
    onIpChange(null);
  };

  return (
    <>
      <div>
        <label style={labelStyle}>Segmento de red</label>
        <select
          value={selectedSegment}
          onChange={(event) => handleSegmentChange(event.target.value)}
          disabled={disabled}
          style={{
            ...inputStyle,
            color: disabled ? '#94a3b8' : '#15803d',
            backgroundColor: disabled ? '#f8fafc' : '#fff',
          }}
        >
          <option value="">Selecciona un segmento...</option>
          {IP_SEGMENTS.map((segment) => {
            const availableCount = filterIpsBySegment(
              availableIps,
              segment.id
            ).length;

            return (
              <option key={segment.id} value={segment.id}>
                {segment.label} ({availableCount} disponibles)
              </option>
            );
          })}
        </select>
      </div>

      <div>
        <label style={labelStyle}>IP disponible</label>
        <select
          value={selectedIp || ''}
          onChange={(event) => onIpChange(event.target.value || null)}
          disabled={disabled || !selectedSegment}
          style={{
            ...inputStyle,
            fontWeight: 'bold',
            color: disabled || !selectedSegment ? '#94a3b8' : '#15803d',
            backgroundColor: disabled || !selectedSegment ? '#f8fafc' : '#fff',
          }}
        >
          <option value="">
            {selectedSegment
              ? 'Sin IP asignada'
              : 'Selecciona primero un segmento'}
          </option>
          {segmentIps.map((ip) => (
            <option key={ip.id} value={ip.direccion_ip}>
              {ip.direccion_ip} ({ip.observacion || 'Libre'})
            </option>
          ))}
        </select>
        {disabled && (
          <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#64748b' }}>
            Las IP solo se pueden asignar o cambiar cuando el usuario está Activo.
          </div>
        )}
      </div>
    </>
  );
}
