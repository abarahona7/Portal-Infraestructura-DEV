// Solo los campos descriptivos se normalizan al escribir. Identificadores,
// correos, contraseñas, IP y números conservan exactamente lo ingresado.
const uppercaseFieldsByModule = {
  usuarios: ['nombre_completo', 'cargo'],
  equipos: ['marca', 'modelo', 'accesorios'],
  perfiles: ['nombre', 'observaciones'],
  ips: ['asignado_otro', 'observacion'],
  anexos: ['observaciones'],
  'pcs-genericos': ['marca', 'modelo', 'observaciones'],
  servidores: ['descripcion'],
};

export const toPortalUppercase = (value) =>
  typeof value === 'string' ? value.toLocaleUpperCase('es-CL') : value;

export const normalizeModalTextChange = (module, previous, next) => {
  if (!next || typeof next !== 'object') return next;

  const fields = uppercaseFieldsByModule[module] || [];
  let normalized = next;

  for (const field of fields) {
    // Al editar otro dato no alteramos campos antiguos que no se tocaron.
    if (typeof next[field] === 'string' && next[field] !== previous?.[field]) {
      normalized = { ...normalized, [field]: toPortalUppercase(next[field]) };
    }
  }

  return normalized;
};
