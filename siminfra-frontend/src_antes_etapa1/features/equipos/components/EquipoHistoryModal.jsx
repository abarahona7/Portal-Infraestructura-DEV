import AuditHistoryModal from '../../../components/common/AuditHistoryModal';

export default function EquipoHistoryModal({ equipo, onClose }) {
  return (
    <AuditHistoryModal
      open={Boolean(equipo)}
      title="Historial de Movimientos"
      subtitle={
        equipo
          ? `${equipo.marca || ''} ${equipo.modelo || ''} — Serie: ${equipo.numero_serie || 'N/I'}`.trim()
          : ''
      }
      entries={equipo?.historial || []}
      emptyMessage="No existen registros de cambios para este equipo."
      onClose={onClose}
    />
  );
}
