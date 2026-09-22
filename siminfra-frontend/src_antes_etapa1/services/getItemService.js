import { getUsuarios } from '../api/usuariosApi';
import { getEquipos } from '../api/equiposApi';
import { getPerfiles } from '../api/perfilesApi';
import { getIps } from '../api/ipsApi';
import { getAnexos } from '../api/anexosApi';
import { getPcsGenericos } from '../api/pcsGenericosApi';
import { getServidores } from '../api/servidoresApi';


export const getItemsByTab = async (
  tab,
  params = {}
) => {
  switch (tab) {
    case 'usuarios':
      return await getUsuarios(params);

    case 'equipos':
      return await getEquipos(params);

    case 'perfiles':
      return await getPerfiles(params);

    case 'ips':
      return await getIps(params);

    case 'anexos':
      return await getAnexos(params);

    case 'pcs-genericos':
      return await getPcsGenericos(params);

    case 'servidores':
      return await getServidores(params);

    default:
      return [];
  }
};