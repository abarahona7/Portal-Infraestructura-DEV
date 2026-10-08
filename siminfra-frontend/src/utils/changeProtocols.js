export const userStatusChecklist = {
  BAJA: [
    { id: 'equipos', label: 'Revisé la devolución física de los equipos e insumos asignados.' },
    { id: 'ip', label: 'Confirmé que se liberará la dirección IP del usuario.' },
    { id: 'anexo', label: 'Confirmé que se liberará el anexo del usuario.' },
  ],
  LICENCIA: [
    { id: 'ip', label: 'Confirmé que se liberará la dirección IP del usuario.' },
    { id: 'custodia', label: 'Verifiqué que sus equipos, insumos y anexo seguirán asignados.' },
  ],
  ACTIVO: [
    { id: 'reactivacion', label: 'Verifiqué los datos y accesos antes de reactivar al usuario.' },
  ],
};

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
