import { createUsuario } from '../api/usuariosApi';
import { createEquipo } from '../api/equiposApi';
import { createPerfil } from '../api/perfilesApi';
import { createIp } from '../api/ipsApi';
import { createAnexo } from '../api/anexosApi';
import { createPcGenerico } from '../api/pcsGenericosApi';
import { createServidor } from '../api/servidoresApi';

export const createItemByTab = async (tab, payload) => {
  switch (tab) {
    case 'usuarios':
      return await createUsuario(payload);

    case 'equipos':
      return await createEquipo(payload);

    case 'perfiles':
      return await createPerfil(payload);

    case 'ips':
      return await createIp(payload);

    case 'anexos':
      return await createAnexo(payload);

    case 'pcs-genericos':
      return await createPcGenerico(payload);

    case 'servidores':
      return await createServidor(payload);

    default:
      throw new Error(
        `Módulo de creación no soportado: ${tab}`
      );
  }
};