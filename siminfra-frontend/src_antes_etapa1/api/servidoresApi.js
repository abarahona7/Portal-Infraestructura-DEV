import apiClient from './client';

export const getServidores = async (params = {}) => {
  const response = await apiClient.get(
    '/servidores/',
    {
      params,
    }
  );

  return response.data;
};

export const createServidor = async (servidor) => {
  const response = await apiClient.post(
    '/servidores/',
    servidor
  );

  return response.data;
};

export const updateServidor = async (
  id,
  servidor
) => {
  const response = await apiClient.patch(
    `/servidores/${id}/`,
    servidor
  );

  return response.data;
};

export const deleteServidor = async (id) => {
  await apiClient.delete(
    `/servidores/${id}/`
  );
};