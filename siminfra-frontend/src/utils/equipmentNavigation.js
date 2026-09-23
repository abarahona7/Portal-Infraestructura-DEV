export const EQUIPMENT_NAV_ITEMS = [
  { id: 'equipos-notebook', category: 'Notebook', label: 'Notebook' },
  { id: 'equipos-celular', category: 'Celular', label: 'Celular' },
  { id: 'equipos-tablet', category: 'Tablet', label: 'Tablet' },
  { id: 'equipos-mac', category: 'Mac', label: 'Mac' },
  { id: 'equipos-bam-router', category: 'BAM / Router', label: 'BAM / Router' },
  { id: 'equipos-perifericos', category: 'PERIFERICOS', label: 'Periféricos' },
];

export const isEquipmentTab = (tab) => (
  EQUIPMENT_NAV_ITEMS.some((item) => item.id === tab)
);

export const getEquipmentCategoryByTab = (tab) => (
  EQUIPMENT_NAV_ITEMS.find((item) => item.id === tab)?.category || ''
);

export const getEquipmentLabelByTab = (tab) => (
  EQUIPMENT_NAV_ITEMS.find((item) => item.id === tab)?.label || 'Equipos'
);

export const getModuleTab = (tab) => (
  isEquipmentTab(tab) ? 'equipos' : tab
);
