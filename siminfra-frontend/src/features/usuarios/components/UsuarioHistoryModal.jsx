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
      getMetaRows={(entry) => [
        entry.modulo_relacionado && {
          label: 'Módulo relacionado',
          value: entry.modulo_relacionado,
        },
        entry.objeto_relacionado_id && {
          label: 'Registro relacionado',
          value: `ID ${entry.objeto_relacionado_id}`,
        },
      ].filter(Boolean)}
      onClose={onClose}
    />
  );
}
