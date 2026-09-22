import EditModal from '../common/EditModal';

import UsuarioEditForm from '../../features/usuarios/components/UsuarioEditForm';
import EquipoEditForm from '../../features/equipos/components/EquipoEditForm';
import PerfilEditForm from '../../features/perfiles/components/PerfilEditForm';
import IpEditForm from '../../features/ips/components/IpEditForm';
import AnexoEditForm from '../../features/anexos/components/AnexoEditForm';
import PCGenericoEditForm from '../../features/pcsGenericos/components/PCGenericoEditForm';
import ServidorEditForm from '../../features/servidores/components/ServidorEditForm';

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
  departments,
  usuarios,
  availableIps,
  formatEquipmentType,
  onHostnameChange,
  onIpChange,
}) {
  if (!editingItem) return null;

  return (
    <EditModal
      title={getEditTitle(tab)}
      onClose={onClose}
      onSubmit={onSubmit}
    >
      {tab === 'usuarios' && (
        <UsuarioEditForm
          usuario={editingItem}
          onChange={setEditingItem}
          departments={departments}
          availableIps={availableIps}
        />
      )}

      {tab === 'equipos' && (
        <EquipoEditForm
          equipo={editingItem}
          onChange={setEditingItem}
          usuarios={usuarios}
          formatEquipmentType={formatEquipmentType}
          onHostnameChange={onHostnameChange}
        />
      )}

      {tab === 'perfiles' && (
        <PerfilEditForm
          perfil={editingItem}
          onChange={setEditingItem}
          departments={departments}
        />
      )}

      {tab === 'ips' && (
        <IpEditForm
          ip={editingItem}
          onChange={setEditingItem}
          usuarios={usuarios}
          onIpChange={onIpChange}
        />
      )}

      {tab === 'anexos' && (
        <AnexoEditForm
          anexo={editingItem}
          onChange={setEditingItem}
          usuarios={usuarios}
        />
      )}

      {tab === 'pcs-genericos' && (
        <PCGenericoEditForm
          pc={editingItem}
          onChange={setEditingItem}
          departments={departments}
        />
      )}

      {tab === 'servidores' && (
        <ServidorEditForm
          servidor={editingItem}
          onChange={setEditingItem}
        />
      )}
    </EditModal>
  );
}