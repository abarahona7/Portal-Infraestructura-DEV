import AuditHistoryModal from '../../../components/common/AuditHistoryModal';

export default function IpHistoryModal({ ip, onClose }) {
  const entries = (ip?.historial || []).map((entry) => ({
    ...entry,
    accion: entry.accion_nombre || entry.accion,
    modificado_por: entry.realizado_por,
  }));

  return (
    <AuditHistoryModal
      open={Boolean(ip)}
      title="Historial de asignaciones IP"
      subtitle={ip ? `Dirección IP: ${ip.direccion_ip}` : ''}
      entries={entries}
      emptyMessage="Esta dirección IP todavía no registra asignaciones ni liberaciones."
      onClose={onClose}
      getMetaRows={(entry) => [
        {
          label: 'Tipo de asignación',
          value: entry.tipo_nombre || 'Sin tipo registrado',
        },
        {
          label: 'Propietario',
          value: entry.propietario_nombre || 'Sin propietario registrado',
        },
      ]}
    />
  );
}
