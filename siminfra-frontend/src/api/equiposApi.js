import apiClient from './client';

export const getEquipos = async (params = {}, requestConfig = {}) => {
  const response = await apiClient.get('/equipos/', {
    ...requestConfig,
    params,
  });

  return response.data;
};

export const createEquipo = async (equipo) => {
  const response = await apiClient.post('/equipos/', equipo);

  return response.data;
};

export const updateEquipo = async (id, equipo) => {
  const response = await apiClient.patch(`/equipos/${id}/`, equipo);

  return response.data;
};

export const deleteEquipo = async (id) => {
  await apiClient.delete(`/equipos/${id}/`);
};
