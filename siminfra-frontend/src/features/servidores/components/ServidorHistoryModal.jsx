import AuditHistoryModal from '../../../components/common/AuditHistoryModal';

export default function ServidorHistoryModal({ servidor, onClose }) {
  return (
    <AuditHistoryModal
      open={Boolean(servidor)}
      title="Historial de Servidor"
      subtitle={
        servidor
          ? `${servidor.hostname || 'Sin hostname'} — IP: ${servidor.ip || 'Sin IP'}`
          : ''
      }
      entries={servidor?.historial || []}
      emptyMessage="No existen registros de cambios para este servidor."
      onClose={onClose}
    />
  );
}
