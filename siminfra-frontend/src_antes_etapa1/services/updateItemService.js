import { updateUsuario } from '../api/usuariosApi';
import { updateEquipo } from '../api/equiposApi';
import { updatePerfil } from '../api/perfilesApi';
import { updateIp } from '../api/ipsApi';
import { updateAnexo } from '../api/anexosApi';
import { updatePcGenerico } from '../api/pcsGenericosApi';
import { updateServidor } from '../api/servidoresApi';

export const updateItemByTab = async (
  tab,
  id,
  payload
) => {
  switch (tab) {
    case 'usuarios':
      return await updateUsuario(id, payload);

    case 'equipos':
      return await updateEquipo(id, payload);

    case 'perfiles':
      return await updatePerfil(id, payload);

    case 'ips':
      return await updateIp(id, payload);

    case 'anexos':
      return await updateAnexo(id, payload);

    case 'pcs-genericos':
      return await updatePcGenerico(id, payload);

    case 'servidores':
      return await updateServidor(id, payload);

    default:
      throw new Error(
        `Módulo de edición no soportado: ${tab}`
      );
  }
};