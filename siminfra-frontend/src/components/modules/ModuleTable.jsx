import UsuariosTable from '../../features/usuarios/components/UsuariosTable';
import EquiposTable from '../../features/equipos/components/EquiposTable';
import PerfilesTable from '../../features/perfiles/components/PerfilesTable';
import IpsTable from '../../features/ips/components/IpsTable';
import AnexosTable from '../../features/anexos/components/AnexosTable';
import PCsGenericosTable from '../../features/pcsGenericos/components/PCsGenericosTable';
import ServidoresTable from '../../features/servidores/components/ServidoresTable';

export default function ModuleTable({
  tab,
  data,
  formatEquipmentType,
  renderUsuarioStatusBadge,
  renderAccountTypeBadge,
  renderIpStatusBadge,
  onSelectUser,
  onShowUserHistory,
  onShowEquipmentHistory,
  onSelectEquipment,
  onShowIpHistory,
  onShowProfileHistory,
  onEdit,
  onToggleProfileStatus,
  renderAnexoStatusBadge,
  onShowAnexoHistory,
  onShowPCGenericoHistory,
  onShowServidorHistory,
  role,
  onRevealSecret,
}) {
  if (tab === 'usuarios') {
    return (
      <UsuariosTable
        usuarios={data}
        onSelectUser={onSelectUser}
        onShowHistory={onShowUserHistory}
        onEdit={onEdit}
        role={role}
        onRevealSecret={onRevealSecret}
        renderStatusBadge={renderUsuarioStatusBadge}
      />
    );
  }

  if (tab === 'equipos') {
    return (
      <EquiposTable
        equipos={data}
        formatEquipmentType={formatEquipmentType}
        onShowHistory={onShowEquipmentHistory}
        onSelectEquipment={onSelectEquipment}
        onEdit={onEdit}
        role={role}
        onRevealSecret={onRevealSecret}
      />
    );
  }

  if (tab === 'perfiles') {
    return (
      <PerfilesTable
        perfiles={data}
        renderAccountTypeBadge={renderAccountTypeBadge}
        onShowHistory={onShowProfileHistory}
        onEdit={onEdit}
        onToggleStatus={onToggleProfileStatus}
        role={role}
        onRevealSecret={onRevealSecret}
      />
    );
  }

  if (tab === 'ips') {
    return (
      <IpsTable
        ips={data}
        renderIpStatusBadge={renderIpStatusBadge}
        onShowHistory={onShowIpHistory}
        onEdit={onEdit}
      />
    );
  }

  if (tab === 'anexos') {
    return (
      <AnexosTable
        anexos={data}
        renderAnexoStatusBadge={renderAnexoStatusBadge}
        onShowHistory={onShowAnexoHistory}
        onEdit={onEdit}
        role={role}
      />
    );
  }

  if (tab === 'pcs-genericos') {
    return (
      <PCsGenericosTable
        pcs={data}
        onShowHistory={onShowPCGenericoHistory}
        onEdit={onEdit}
        role={role}
        onRevealSecret={onRevealSecret}
      />
    );
  }

  if (tab === 'servidores') {
    return (
      <ServidoresTable
        servidores={data}
        onShowHistory={onShowServidorHistory}
        onEdit={onEdit}
      />
    );
  }

  return null;
}
