import apiClient from './client';

export const getAnexos = async (params = {}, requestConfig = {}) => {
  const response = await apiClient.get('/anexos/', {
    ...requestConfig,
    params,
  });

  return response.data;
};

export const createAnexo = async (anexo) => {
  const response = await apiClient.post('/anexos/', anexo);

  return response.data;
};

export const updateAnexo = async (id, anexo) => {
  const response = await apiClient.patch(`/anexos/${id}/`, anexo);

  return response.data;
};

export const deleteAnexo = async (id) => {
  await apiClient.delete(`/anexos/${id}/`);
};
