export const formatEquipmentType = (tipo) => {
  if (!tipo) return 'N/I';

  const normalizedType = tipo.toUpperCase();

  if (normalizedType === 'NTBK' || normalizedType === 'NOTEBOOK') {
    return 'Notebook';
  }

  if (normalizedType === 'CEL' || normalizedType === 'CELULAR') {
    return 'Celular';
  }

  if (normalizedType === 'TBIT' || normalizedType === 'TABLET') {
    return 'Tablet';
  }

  if (normalizedType === 'MAC') {
    return 'Mac';
  }

  if (
    normalizedType === 'BAM' ||
    normalizedType === 'BAM / ROUTER'
  ) {
    return 'BAM / Router';
  }

  return tipo;
};