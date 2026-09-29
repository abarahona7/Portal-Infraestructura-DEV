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
  params = {},
  requestConfig = {}
) => {
  switch (tab) {
    case 'usuarios':
      return getUsuarios(params, requestConfig);

    case 'equipos':
      return getEquipos(params, requestConfig);

    case 'perfiles':
      return getPerfiles(params, requestConfig);

    case 'ips':
      return getIps(params, requestConfig);

    case 'anexos':
      return getAnexos(params, requestConfig);

    case 'pcs-genericos':
      return getPcsGenericos(params, requestConfig);

    case 'servidores':
      return getServidores(params, requestConfig);

    case 'departamentos':
      return getDepartamentos(params, requestConfig);

    default:
      return [];
  }
};

export const getItemsByTab = (tab, params = {}, requestConfig = {}) => {
  if (requestConfig.signal) {
    return fetchItemsByTab(tab, params, requestConfig);
  }

  const key = buildRequestKey(tab, params);
  if (pendingRequests.has(key)) {
    return pendingRequests.get(key);
  }

  const request = Promise.resolve(fetchItemsByTab(tab, params, requestConfig))
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
