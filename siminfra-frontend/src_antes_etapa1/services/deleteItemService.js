import { deleteUsuario } from '../api/usuariosApi';
import { deleteEquipo } from '../api/equiposApi';
import { deletePerfil } from '../api/perfilesApi';
import { deleteIp } from '../api/ipsApi';
import { deleteAnexo } from '../api/anexosApi';
import { deletePcGenerico } from '../api/pcsGenericosApi';
import { deleteServidor } from '../api/servidoresApi';

export const deleteItemByTab = async (tab, id) => {
  switch (tab) {
    case 'usuarios':
      return await deleteUsuario(id);

    case 'equipos':
      return await deleteEquipo(id);

    case 'perfiles':
      return await deletePerfil(id);

    case 'ips':
      return await deleteIp(id);

    case 'anexos':
      return await deleteAnexo(id);

    case 'pcs-genericos':
      return await deletePcGenerico(id);

    case 'servidores':
      return await deleteServidor(id);

    default:
      throw new Error(
        `Módulo de eliminación no soportado: ${tab}`
      );
  }
};