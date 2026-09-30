import apiClient from './client';

export const getMovimientos = async (params = {}, signal) => {
  const { data } = await apiClient.get('/movimientos/', { params, signal });
  return data;
};

export const createMovimiento = async (payload) => {
  const { data } = await apiClient.post('/movimientos/', payload);
  return data;
};

export const downloadActa = async (acta) => {
  const { data } = await apiClient.get(`/actas/${acta.id}/pdf/`, { responseType: 'blob' });
  const url = URL.createObjectURL(data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${acta.folio}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

export const movimientoError = (error) => {
  const detail = error.response?.data;
  if (!detail || detail instanceof Blob) return 'No se pudo completar la operación. Intenta nuevamente.';
  const messages = (value) => {
    if (Array.isArray(value)) return value.flatMap(messages);
    if (value && typeof value === 'object') return Object.values(value).flatMap(messages);
    return typeof value === 'string' ? [value] : [];
  };
  return messages(detail).join(' ') || 'No se pudo completar la operación.';
};

export const getActaEventos = async (actaId, signal) => {
  const { data } = await apiClient.get(`/actas/${actaId}/eventos/`, { signal });
  return data;
};

export const cambiarEstadoActa = async (actaId, estadoNuevo, motivo, archivoFirmado) => {
  const payload = new FormData();
  payload.append('estado_nuevo', estadoNuevo);
  payload.append('motivo', motivo);
  if (archivoFirmado) payload.append('archivo_firmado', archivoFirmado);
  const { data } = await apiClient.post(`/actas/${actaId}/estado/`, payload, { headers: { 'Content-Type': 'multipart/form-data' } });
  return data;
};

export const downloadActaFirmada = async (acta) => {
  const { data } = await apiClient.get(`/actas/${acta.id}/firmada/`, { responseType: 'blob' });
  const url = URL.createObjectURL(data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${acta.folio}-copia-firmada.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
