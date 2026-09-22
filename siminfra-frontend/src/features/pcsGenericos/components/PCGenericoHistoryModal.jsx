import AuditHistoryModal from '../../../components/common/AuditHistoryModal';

export default function PCGenericoHistoryModal({ pc, onClose }) {
  return (
    <AuditHistoryModal
      open={Boolean(pc)}
      title="Historial de PC Genérico"
      subtitle={
        pc
          ? `${pc.hostname || 'Sin hostname'}${pc.usuario_local ? ` — ${pc.usuario_local}` : ''}`
          : ''
      }
      entries={pc?.historial || []}
      emptyMessage="No existen registros de cambios para este PC Genérico."
      onClose={onClose}
    />
  );
}
