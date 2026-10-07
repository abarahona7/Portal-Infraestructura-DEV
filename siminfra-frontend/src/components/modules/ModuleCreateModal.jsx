import CreateModal from '../common/CreateModal';

import UsuarioCreateForm from '../../features/usuarios/components/UsuarioCreateForm';
import EquipoCreateForm from '../../features/equipos/components/EquipoCreateForm';
import PerfilCreateForm from '../../features/perfiles/components/PerfilCreateForm';
import IpCreateForm from '../../features/ips/components/IpCreateForm';
import AnexoCreateForm from '../../features/anexos/components/AnexoCreateForm';
import PCGenericoCreateForm from '../../features/pcsGenericos/components/PCGenericoCreateForm';
import ServidorCreateForm from '../../features/servidores/components/ServidorCreateForm';
import { normalizeModalTextChange } from '../../utils/normalizeModalText';

const getCreateTitle = (tab) => {
  switch (tab) {
    case 'usuarios':
      return 'Nuevo Usuario';

    case 'equipos':
      return 'Nuevo Equipo';

    case 'perfiles':
      return 'Nuevo Perfil Genérico';

    case 'ips':
      return 'Nueva Dirección IP';

    case 'anexos':
      return 'Nuevo Anexo';

    case 'pcs-genericos':
      return 'Nuevo PC Genérico';

    case 'servidores':
      return 'Nuevo Servidor';

    default:
      return 'Nuevo Registro';
  }
};

export default function ModuleCreateModal({
  tab,
  newItem,
  setNewItem,
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
  if (!newItem) return null;

  const updateItem = (next) => {
    setNewItem((previous) => normalizeModalTextChange(tab, previous, next));
  };

  return (
    <CreateModal
      title={getCreateTitle(tab)}
      onClose={onClose}
      onSubmit={onSubmit}
    >
      {tab === 'usuarios' && (
        <UsuarioCreateForm
          usuario={newItem}
          onChange={updateItem}
          departments={departmentCatalog}
          availableIps={availableIps}
        />
      )}

      {tab === 'equipos' && (
        <EquipoCreateForm
          equipo={newItem}
          onChange={updateItem}
          usuarios={usuarios}
          formatEquipmentType={formatEquipmentType}
          onHostnameChange={onHostnameChange}
          category={equipmentCategory}
        />
      )}

      {tab === 'perfiles' && (
        <PerfilCreateForm
          perfil={newItem}
          onChange={updateItem}
          departments={departmentCatalog}
        />
      )}

      {tab === 'ips' && (
        <IpCreateForm
          ip={newItem}
          onChange={updateItem}
          usuarios={usuarios}
          onIpChange={onIpChange}
        />
      )}

      {tab === 'anexos' && (
        <AnexoCreateForm
          anexo={newItem}
          onChange={updateItem}
          usuarios={usuarios}
        />
      )}

      {tab === 'pcs-genericos' && (
        <PCGenericoCreateForm
          pc={newItem}
          onChange={updateItem}
          departments={departmentCatalog}
          availableIps={availableIps}
        />
      )}

      {tab === 'servidores' && (
        <ServidorCreateForm
          servidor={newItem}
          onChange={updateItem}
          availableIps={availableIps}
        />
      )}
    </CreateModal>
  );
}
