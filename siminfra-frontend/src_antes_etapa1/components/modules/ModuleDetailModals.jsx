import UsuarioDetailModal from '../../features/usuarios/components/UsuarioDetailModal';
import UsuarioHistoryModal from '../../features/usuarios/components/UsuarioHistoryModal';
import EquipoHistoryModal from '../../features/equipos/components/EquipoHistoryModal';
import AnexoHistoryModal from '../../features/anexos/components/AnexoHistoryModal';
import PCGenericoHistoryModal from '../../features/pcsGenericos/components/PCGenericoHistoryModal';

export default function ModuleDetailModals({
  selectedUser,
  historyUsuario,
  historyEquipo,
  historyAnexo,
  onCloseAnexoHistory,
  onCloseUser,
  onCloseUserHistory,
  onCloseEquipmentHistory,
  renderUsuarioStatusBadge,
  formatEquipmentType,
  historyPCGenerico,
onClosePCGenericoHistory,
role,
onRevealSecret,
}) {

  return (
    <>
      <UsuarioDetailModal
        usuario={selectedUser}
        onClose={onCloseUser}
        renderStatusBadge={renderUsuarioStatusBadge}
        formatEquipmentType={formatEquipmentType}
        role={role}
        onRevealSecret={onRevealSecret}
      />

      <UsuarioHistoryModal
        usuario={historyUsuario}
        onClose={onCloseUserHistory}
      />

      <EquipoHistoryModal
        equipo={historyEquipo}
        onClose={onCloseEquipmentHistory}

      />

      <AnexoHistoryModal
        anexo={historyAnexo}
        onClose={onCloseAnexoHistory}
      />

      <PCGenericoHistoryModal
        pc={historyPCGenerico}
        onClose={onClosePCGenericoHistory}

      />
    </>
  );
}