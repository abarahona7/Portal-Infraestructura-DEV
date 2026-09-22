import apiClient from './client';

export const getPcsGenericos = async (params = {}) => {
  const response = await apiClient.get(
    '/pcs-genericos/',
    { params }
  );

  return response.data;
};

export const createPcGenerico = async (pc) => {
  const response = await apiClient.post(
    '/pcs-genericos/',
    pc
  );

  return response.data;
};

export const updatePcGenerico = async (id, pc) => {
  const response = await apiClient.patch(
    `/pcs-genericos/${id}/`,
    pc
  );

  return response.data;
};

export const deletePcGenerico = async (id) => {
  await apiClient.delete(
    `/pcs-genericos/${id}/`
  );
};