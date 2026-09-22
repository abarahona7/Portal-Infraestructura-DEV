import apiClient from './client';

export const getDepartamentos = async (params = {}) => {
  const response = await apiClient.get('/departamentos/', { params });
  return response.data;
};

export const createDepartamento = async (payload) => {
  const response = await apiClient.post('/departamentos/', payload);
  return response.data;
};

export const updateDepartamento = async (id, payload) => {
  const response = await apiClient.patch(`/departamentos/${id}/`, payload);
  return response.data;
};

export const deleteDepartamento = async (id) => {
  await apiClient.delete(`/departamentos/${id}/`);
};

export const getSubareas = async (params = {}) => {
  const response = await apiClient.get('/subareas/', { params });
  return response.data;
};

export const createSubarea = async (payload) => {
  const response = await apiClient.post('/subareas/', payload);
  return response.data;
};

export const updateSubarea = async (id, payload) => {
  const response = await apiClient.patch(`/subareas/${id}/`, payload);
  return response.data;
};

export const deleteSubarea = async (id) => {
  await apiClient.delete(`/subareas/${id}/`);
};
