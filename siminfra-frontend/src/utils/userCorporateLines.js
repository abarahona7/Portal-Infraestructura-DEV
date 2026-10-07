const isCellularEquipment = (equipo) => ['CEL', 'CELULAR'].includes(
  String(equipo?.tipo || '').trim().toUpperCase()
);

export const normalizeCorporateLineInput = (value) => {
  const digits = String(value || '').replace(/[^0-9]/g, '');
  const localDigits = digits.length > 8 && digits.startsWith('569')
    ? digits.slice(3, 11)
    : digits.slice(0, 8);
  return localDigits ? `+569${localDigits}` : '';
};

export const getCorporateLineDigits = (value) => {
  const line = String(value || '');
  return line.startsWith('+569') ? line.slice(4, 12) : '';
};

export const getAssignedCellularDevices = (usuario) => (usuario?.equipos || [])
  .filter(isCellularEquipment);

export const getAssignedCellularNumbers = (usuario) => [
  ...new Set(
    getAssignedCellularDevices(usuario)
      .map((equipo) => String(equipo.numero_telefono || '').trim())
      .filter(Boolean)
  ),
];

export const getCorporateLineNumbers = (usuario) => [
  ...new Set([
    String(usuario?.celular || '').trim(),
    ...getAssignedCellularNumbers(usuario),
  ].filter(Boolean)),
];
