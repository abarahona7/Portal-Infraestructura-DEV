import { useEffect, useState } from 'react';
import { EQUIPMENT_NAV_ITEMS } from '../utils/equipmentNavigation';

const ACTIVE_TAB_KEY = 'portal-infra-ti-chile-active-tab';
const SIDEBAR_KEY = 'portal-infra-ti-chile-sidebar-collapsed';

const VALID_TABS = new Set([
  'usuarios',
  'activos-resumen',
  'pcs-genericos',
  'servidores',
  'perfiles',
  'ips',
  'anexos',
  'departamentos',
  ...EQUIPMENT_NAV_ITEMS.map((item) => item.id),
]);

const readSavedTab = () => {
  try {
    const saved = sessionStorage.getItem(ACTIVE_TAB_KEY);
    if (saved === 'equipos' || saved === 'activos-consultas') return 'pcs-genericos';
    return VALID_TABS.has(saved) ? saved : 'usuarios';
  } catch {
    return 'usuarios';
  }
};

const saveTab = (tab) => {
  try {
    sessionStorage.setItem(ACTIVE_TAB_KEY, tab);
  } catch {
    // Continuar sin persistencia si sessionStorage no está disponible.
  }
};

export const useModuleNavigation = (resetFilters, role) => {
  const [tab, setTab] = useState(readSavedTab);

  // Drawer para tablet / móvil
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Estado expandido / contraído en escritorio
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      const savedValue = localStorage.getItem(SIDEBAR_KEY);
      return savedValue === 'true';
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(
        SIDEBAR_KEY,
        String(sidebarCollapsed)
      );
    } catch {
      // Si localStorage no está disponible, continuamos sin guardar.
    }
  }, [sidebarCollapsed]);

  // El Visualizador solo puede navegar por Anexos. Esto complementa,
  // pero no reemplaza, la restricción aplicada en el backend.
  useEffect(() => {
    if (role === 'Visualizador') {
      saveTab('anexos');
    }
  }, [role]);

  const selectTab = (selectedTab) => {
    const nextTab = selectedTab === 'equipos'
      ? 'pcs-genericos'
      : selectedTab;

    if (!VALID_TABS.has(nextTab)) {
      return;
    }

    if (role === 'Visualizador' && nextTab !== 'anexos') {
      return;
    }

    setTab(nextTab);
    saveTab(nextTab);
    resetFilters?.();
    setSidebarOpen(false);
  };

  const openSidebar = () => setSidebarOpen(true);
  const closeSidebar = () => setSidebarOpen(false);
  const toggleSidebarCollapsed = () => setSidebarCollapsed((prev) => !prev);

  const activeTab = role === 'Visualizador' ? 'anexos' : tab;

  return {
    tab: activeTab,
    sidebarOpen,
    openSidebar,
    closeSidebar,
    sidebarCollapsed,
    toggleSidebarCollapsed,
    selectTab,
  };
};
