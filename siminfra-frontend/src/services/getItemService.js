import { getUsuarios } from '../api/usuariosApi';
import { getEquipos } from '../api/equiposApi';
import { getPerfiles } from '../api/perfilesApi';
import { getIps } from '../api/ipsApi';
import { getAnexos } from '../api/anexosApi';
import { getPcsGenericos } from '../api/pcsGenericosApi';
import { getServidores } from '../api/servidoresApi';
import { getDepartamentos } from '../api/departamentosApi';
import apiClient from '../api/client';


const pendingRequests = new Map();

const buildRequestKey = (tab, params) => JSON.stringify([
  tab,
  Object.entries(params).sort(([left], [right]) => left.localeCompare(right)),
]);

const fetchItemsByTab = (
  tab,
  params = {}
) => {
  switch (tab) {
    case 'usuarios':
      return getUsuarios(params);

    case 'equipos':
      return getEquipos(params);

    case 'perfiles':
      return getPerfiles(params);

    case 'ips':
      return getIps(params);

    case 'anexos':
      return getAnexos(params);

    case 'pcs-genericos':
      return getPcsGenericos(params);

    case 'servidores':
      return getServidores(params);

    case 'departamentos':
      return getDepartamentos(params);

    default:
      return [];
  }
};

export const getItemsByTab = (tab, params = {}) => {
  const key = buildRequestKey(tab, params);
  if (pendingRequests.has(key)) {
    return pendingRequests.get(key);
  }

  const request = Promise.resolve(fetchItemsByTab(tab, params))
    .finally(() => pendingRequests.delete(key));

  pendingRequests.set(key, request);
  return request;
};

const detailPaths = {
  usuarios: 'usuarios',
  equipos: 'equipos',
  perfiles: 'perfiles-genericos',
  anexos: 'anexos',
  'pcs-genericos': 'pcs-genericos',
  servidores: 'servidores',
};

export const getItemDetailsByTab = async (tab, id) => {
  const path = detailPaths[tab];
  if (!path) {
    throw new Error(`El módulo ${tab} no dispone de detalle diferido.`);
  }

  const response = await apiClient.get(`/${path}/${id}/`);
  return response.data;
};
