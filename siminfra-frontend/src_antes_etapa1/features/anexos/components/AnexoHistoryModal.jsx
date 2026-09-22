import AuditHistoryModal from '../../../components/common/AuditHistoryModal';

export default function AnexoHistoryModal({ anexo, onClose }) {
  return (
    <AuditHistoryModal
      open={Boolean(anexo)}
      title="Historial de Anexo"
      subtitle={anexo ? `Anexo: ${anexo.numero_anexo}` : ''}
      entries={anexo?.historial || []}
      emptyMessage="No existen registros de cambios para este anexo."
      onClose={onClose}
      getMetaRows={(entry) => {
        const rows = [];

        if (entry.usuario_anterior) {
          rows.push({
            label: 'Usuario anterior',
            value: entry.usuario_anterior,
          });
        }

        if (entry.usuario_nuevo) {
          rows.push({
            label: 'Usuario actual',
            value: entry.usuario_nuevo,
          });
        }

        return rows;
      }}
    />
  );
}
