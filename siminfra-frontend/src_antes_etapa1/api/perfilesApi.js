import apiClient from './client';

export const getPerfiles = async (params = {}) => {
  const response = await apiClient.get('/perfiles-genericos/', {
    params,
  });

  return response.data;
};

export const createPerfil = async (perfil) => {
  const response = await apiClient.post(
    '/perfiles-genericos/',
    perfil
  );

  return response.data;
};

export const updatePerfil = async (id, perfil) => {
  const response = await apiClient.patch(
    `/perfiles-genericos/${id}/`,
    perfil
  );

  return response.data;
};

export const deletePerfil = async (id) => {
  await apiClient.delete(`/perfiles-genericos/${id}/`);
};