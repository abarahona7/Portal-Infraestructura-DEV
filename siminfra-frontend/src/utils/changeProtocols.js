export const equipmentChecklist = [
  { id: 'custodia', label: 'Verifiqué físicamente la entrega o devolución del equipo.' },
  { id: 'identidad', label: 'Comprobé la identidad del usuario asignado, cuando corresponde.' },
  { id: 'estado', label: 'Revisé que el estado y la asignación registrados sean correctos.' },
];

export const needsEquipmentChecklist = (original, edited) => {
  if (!original) return false;
  const nextUser = edited.usuario || null;
  let nextState = edited.estado;
  if (!nextUser && nextState === 'ASIGNADO') nextState = 'STOCK';
  if (nextUser && nextState === 'STOCK') nextState = 'ASIGNADO';
  return String(original.usuario || '') !== String(nextUser || '') || original.estado !== nextState;
};
