import EditModal from '../common/EditModal';

import UsuarioEditForm from '../../features/usuarios/components/UsuarioEditForm';
import EquipoEditForm from '../../features/equipos/components/EquipoEditForm';
import PerfilEditForm from '../../features/perfiles/components/PerfilEditForm';
import IpEditForm from '../../features/ips/components/IpEditForm';
import AnexoEditForm from '../../features/anexos/components/AnexoEditForm';
import PCGenericoEditForm from '../../features/pcsGenericos/components/PCGenericoEditForm';
import ServidorEditForm from '../../features/servidores/components/ServidorEditForm';
import { normalizeModalTextChange } from '../../utils/normalizeModalText';

const getEditTitle = (tab) => {
  switch (tab) {
    case 'usuarios':
      return 'Editar Usuario';

    case 'equipos':
      return 'Editar Equipo';

    case 'perfiles':
      return 'Editar Perfil Genérico';

    case 'ips':
      return 'Editar Dirección IP';

    case 'anexos':
      return 'Editar Anexo';

    case 'pcs-genericos':
      return 'Editar PC Genérico';

    case 'servidores':
      return 'Editar Servidor';

    default:
      return 'Editar Registro';
  }
};

export default function ModuleEditModal({
  tab,
  editingItem,
  setEditingItem,
  onSubmit,
  onClose,
  departmentCatalog,
  usuarios,
  availableIps,
  formatEquipmentType,
  onHostnameChange,
  equipmentCategory,
  onIpChange,
}) {
  if (!editingItem) return null;

  const updateItem = (next) => {
    setEditingItem((previous) => normalizeModalTextChange(tab, previous, next));
  };

  return (
    <EditModal
      title={getEditTitle(tab)}
      onClose={onClose}
      onSubmit={onSubmit}
    >
      {tab === 'usuarios' && (
        <UsuarioEditForm
          usuario={editingItem}
          onChange={updateItem}
          departments={departmentCatalog}
          availableIps={availableIps}
        />
      )}

      {tab === 'equipos' && (
        <EquipoEditForm
          equipo={editingItem}
          onChange={updateItem}
          usuarios={usuarios}
          formatEquipmentType={formatEquipmentType}
          onHostnameChange={onHostnameChange}
          category={equipmentCategory}
        />
      )}

      {tab === 'perfiles' && (
        <PerfilEditForm
          perfil={editingItem}
          onChange={updateItem}
          departments={departmentCatalog}
        />
      )}

      {tab === 'ips' && (
        <IpEditForm
          ip={editingItem}
          onChange={updateItem}
          usuarios={usuarios}
          onIpChange={onIpChange}
        />
      )}

      {tab === 'anexos' && (
        <AnexoEditForm
          anexo={editingItem}
          onChange={updateItem}
          usuarios={usuarios}
        />
      )}

      {tab === 'pcs-genericos' && (
        <PCGenericoEditForm
          pc={editingItem}
          onChange={updateItem}
          departments={departmentCatalog}
          availableIps={availableIps}
        />
      )}

      {tab === 'servidores' && (
        <ServidorEditForm
          servidor={editingItem}
          onChange={updateItem}
          availableIps={availableIps}
        />
      )}
    </EditModal>
  );
}
