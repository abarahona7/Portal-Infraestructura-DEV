import AuditHistoryModal from '../../../components/common/AuditHistoryModal';

export default function PerfilHistoryModal({ perfil, onClose }) {
  return (
    <AuditHistoryModal
      open={Boolean(perfil)}
      title="Historial de Perfil Genérico"
      subtitle={
        perfil
          ? `${perfil.nombre || 'Sin nombre'} — Usuario: ${perfil.usuario || 'N/I'}`
          : ''
      }
      entries={perfil?.historial || []}
      emptyMessage="No existen registros de cambios para este perfil genérico."
      onClose={onClose}
    />
  );
}
