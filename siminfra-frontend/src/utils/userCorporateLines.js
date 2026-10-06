const isCellularEquipment = (equipo) => ['CEL', 'CELULAR'].includes(
  String(equipo?.tipo || '').trim().toUpperCase()
);

export const normalizeCorporateLineInput = (value) => {
  const digits = String(value || '').replace(/[^0-9]/g, '').slice(0, 11);
  return digits ? `+${digits}` : '';
};

export const getAssignedCellularNumbers = (usuario) => [
  ...new Set(
    (usuario?.equipos || [])
      .filter(isCellularEquipment)
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
