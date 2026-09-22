import { useEffect, useState } from 'react';

const ACTIVE_TAB_KEY = 'portal-infra-ti-chile-active-tab';
const SIDEBAR_KEY = 'portal-infra-ti-chile-sidebar-collapsed';

const VALID_TABS = new Set([
  'usuarios',
  'equipos',
  'pcs-genericos',
  'servidores',
  'perfiles',
  'ips',
  'anexos',
]);

const readSavedTab = () => {
  try {
    const saved = sessionStorage.getItem(ACTIVE_TAB_KEY);
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
    if (role === 'Visualizador' && tab !== 'anexos') {
      setTab('anexos');
      saveTab('anexos');
      resetFilters?.();
    }
  }, [role, tab, resetFilters]);

  const selectTab = (selectedTab) => {
    if (!VALID_TABS.has(selectedTab)) {
      return;
    }

    if (role === 'Visualizador' && selectedTab !== 'anexos') {
      return;
    }

    setTab(selectedTab);
    saveTab(selectedTab);
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
