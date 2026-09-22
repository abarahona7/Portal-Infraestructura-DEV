import AuditHistoryModal from '../../../components/common/AuditHistoryModal';

export default function UsuarioHistoryModal({ usuario, onClose }) {
  return (
    <AuditHistoryModal
      open={Boolean(usuario)}
      title="Historial de Modificaciones"
      subtitle={
        usuario
          ? `${usuario.nombre_completo} — Red: ${usuario.usuario_red}`
          : ''
      }
      entries={usuario?.historial || []}
      emptyMessage="No existen registros de modificaciones para este usuario."
      onClose={onClose}
    />
  );
}
