import apiClient from './client';

export const getIps = async (params = {}) => {
  const response = await apiClient.get('/ips/', {
    params,
  });

  return response.data;
};

export const createIp = async (ip) => {
  const response = await apiClient.post('/ips/', ip);

  return response.data;
};

export const updateIp = async (id, ip) => {
  const response = await apiClient.patch(`/ips/${id}/`, ip);

  return response.data;
};

export const deleteIp = async (id) => {
  await apiClient.delete(`/ips/${id}/`);
};