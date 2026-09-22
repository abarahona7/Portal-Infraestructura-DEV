import apiClient from './client';

export const getUsuarios = async (params = {}) => {
  const response = await apiClient.get('/usuarios/', {
    params,
  });

  return response.data;
};

export const createUsuario = async (usuario) => {
  const response = await apiClient.post(
    '/usuarios/',
    usuario
  );

  return response.data;
};

export const updateUsuario = async (id, usuario) => {
  const response = await apiClient.patch(
    `/usuarios/${id}/`,
    usuario
  );

  return response.data;
};

export const deleteUsuario = async (id) => {
  await apiClient.delete(`/usuarios/${id}/`);
};


/* =========================================
   ACTA DE ENTREGA
========================================= */

export const getActaEntregaUsuario = async (id) => {
  const response = await apiClient.get(
    `/usuarios/${id}/acta-entrega/`,
    {
      responseType: 'blob',
    }
  );

  return response.data;
};