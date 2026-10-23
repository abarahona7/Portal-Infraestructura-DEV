const FIELD_LABELS = {
  activo_fijo: 'Activo fijo',
  af: 'Activo fijo',
  asignado_otro: 'Asignación',
  celular: 'Línea móvil',
  confirmaciones: 'Confirmaciones',
  correo: 'Correo',
  correo_corp: 'Correo corporativo',
  departamento: 'Departamento',
  departamento_id: 'Departamento',
  direccion_ip: 'Dirección IP',
  estado: 'Estado',
  exterior: 'Número exterior',
  hostname: 'Hostname',
  imei: 'IMEI',
  ip: 'Dirección IP',
  ip_seleccionada: 'Dirección IP',
  marca: 'Marca',
  modelo: 'Modelo',
  nombre: 'Nombre',
  nombre_completo: 'Nombre completo',
  numero_anexo: 'Número de anexo',
  numero_serie: 'Número de serie',
  numero_telefono: 'Número telefónico',
  protocolo_confirmaciones: 'Protocolo de confirmación',
  subarea: 'Área',
  tipo: 'Tipo',
  usuario: 'Usuario',
  usuario_local: 'Usuario local',
  usuario_red: 'Usuario de red',
  version: 'Versión del registro',
};

const IGNORED_FIELDS = new Set(['code', 'current_version', 'request_id']);
const UNLABELED_FIELDS = new Set(['detail', 'non_field_errors']);

const fieldLabel = (field) => FIELD_LABELS[field]
  || field.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase());

const collectMessages = (value, field = '') => {
  if (typeof value === 'string' || typeof value === 'number') {
    const message = String(value);
    return field && !UNLABELED_FIELDS.has(field)
      ? [`${fieldLabel(field)}: ${message}`]
      : [message];
  }

  if (Array.isArray(value)) {
    return value.flatMap((item) => collectMessages(item, field));
  }

  if (value && typeof value === 'object') {
    return Object.entries(value)
      .filter(([key]) => !IGNORED_FIELDS.has(key))
      .flatMap(([key, item]) => collectMessages(item, key));
  }

  return [];
};

export const getApiErrorMessage = (
  error,
  fallback = 'No fue posible completar la operación.'
) => {
  const response = error?.response;
  const data = response?.data;
  const status = response?.status;

  if (!response) {
    if (error?.code === 'ERR_CANCELED' || error?.name === 'AbortError') {
      return fallback;
    }
    if (!error?.isAxiosError && error?.message) {
      return error.message;
    }
    return 'No se pudo conectar con el servidor. Revisa la red e inténtalo nuevamente.';
  }

  if (status === 401) return 'La sesión expiró. Inicia sesión nuevamente.';
  if (status === 403) return 'No tienes permisos para realizar esta operación.';
  if (status === 404) return 'El registro ya no existe o no está disponible.';
  if (status === 429) return 'Se alcanzó el límite de intentos. Espera un momento e inténtalo nuevamente.';
  if (status >= 500) {
    const requestId = data && typeof data === 'object' ? data.request_id : '';
    return requestId
      ? `El servidor no pudo completar la operación. Código de soporte: ${requestId}`
      : 'El servidor no pudo completar la operación. Inténtalo nuevamente.';
  }

  const messages = collectMessages(data);
  if (messages.length > 0) {
    return [...new Set(messages)].slice(0, 3).join(' · ');
  }

  if (status === 409) return 'El registro cambió. Recarga los datos antes de guardar.';

  return fallback;
};

export const getApiErrorMessageAsync = async (error, fallback) => {
  const data = error?.response?.data;

  if (typeof Blob !== 'undefined' && data instanceof Blob) {
    try {
      const text = await data.text();
      const parsed = JSON.parse(text);
      return getApiErrorMessage({
        ...error,
        response: { ...error.response, data: parsed },
      }, fallback);
    } catch {
      return getApiErrorMessage(error, fallback);
    }
  }

  return getApiErrorMessage(error, fallback);
};
