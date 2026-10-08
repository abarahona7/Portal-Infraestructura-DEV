import React, {
  useCallback,
  useEffect,
  useRef,
  useState
} from 'react';
import './App.css';
import Toast from './components/common/Toast';
import ConfirmModal from './components/common/ConfirmModal';
import SecretRevealModal from './components/common/SecretRevealModal';
import Pagination from './components/common/Pagination';


import UserDepartmentCards
  from './features/usuarios/components/UserDepartmentCards';
import PerfilDepartmentCards
  from './features/perfiles/components/PerfilDepartmentCards';
import { updatePerfil } from './api/perfilesApi';

import IpSegmentCards
  from './features/ips/components/IpSegmentCards';

import { getInitialCreateItem } from './utils/getInitialCreateItem';
import {
  exportUsuariosExcel,
  exportEquiposExcel,
  exportIpsExcel,
  exportServidoresExcel,
  exportPerfilesExcel,
  exportAnexosExcel,
  exportPCsGenericosExcel,
} from './utils/moduleExporters';

import { useModuleCrud } from './hooks/useModuleCrud';



import LoginPage from './features/auth/components/LoginPage';
import ModuleCreateModal from './components/modules/ModuleCreateModal';
import ModuleEditModal from './components/modules/ModuleEditModal';
import ModuleTable from './components/modules/ModuleTable';
import ModuleDetailModals from './components/modules/ModuleDetailModals';

import { useModuleModals } from './hooks/useModuleModals';
import { useAuth } from './hooks/useAuth';
import { useIdleLogout } from './hooks/useIdleLogout';
import { useReferenceData } from './hooks/useReferenceData';
import { useModuleData } from './hooks/useModuleData';
import { useModuleFilters } from './hooks/useModuleFilters';
import { useModuleNavigation } from './hooks/useModuleNavigation';
import { useRealtimeChanges } from './hooks/useRealtimeChanges';

import {
  buildEquipmentStateFromHostname,
} from './utils/equipmentHelpers';
import {
  getEquipmentCategoryByTab,
  getEquipmentLabelByTab,
  getModuleTab,
  isEquipmentTab,
} from './utils/equipmentNavigation';

import {
  sanitizeIpInput,
  getAvailableIpsForUser,
  getAvailableIpsForServer,
  IP_SEGMENTS,
} from './utils/ipHelpers';

import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import ModuleToolbar from './components/layout/ModuleToolbar';
import DepartamentosSubareasPage
  from './features/departamentos/components/DepartamentosSubareasPage';
import AssetDashboard from './features/activos/AssetDashboard';
import PapeleraPage from './features/papelera/PapeleraPage';
import EquipoDetailModal from './features/equipos/components/EquipoDetailModal';

import { formatEquipmentType } from './utils/formatEquipmentType';
import apiClient from './api/client';
import { getIpAssignmentHistory } from './api/ipsApi';
import { getItemDetailsByTab } from './services/getItemService';

import {
  renderUsuarioStatusBadge,
  renderAccountTypeBadge,
  renderIpStatusBadge,
  renderAnexoStatusBadge,
} from './components/common/badgeRenderers';

export default function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const [toast, setToast] = useState({
    message: '',
    type: 'success',
  });

  const [confirmModal, setConfirmModal] = useState({
    open: false,
    title: '',
    message: '',
    confirmText: 'Confirmar',
    cancelText: 'Cancelar',
    danger: false,
    checklist: [],
  });

  const [secretRequest, setSecretRequest] = useState(null);
  const [legacyQrToken, setLegacyQrToken] = useState(() => window.location.pathname.match(/^\/qr\/a\/([0-9a-f-]{36})\/?$/i)?.[1] || null);
  const [selectedEquipmentId, setSelectedEquipmentId] = useState(null);
  const [dashboardRevision, setDashboardRevision] = useState(0);
  const [equipmentDetailRevision, setEquipmentDetailRevision] = useState(0);

  const confirmResolverRef = useRef(null);

  const requestConfirmation = ({
    title = 'Confirmar acción',
    message,
    confirmText = 'Confirmar',
    cancelText = 'Cancelar',
    danger = false,
    checklist = [],
  }) => {
    return new Promise((resolve) => {
      confirmResolverRef.current = resolve;

      setConfirmModal({
        open: true,
        title,
        message,
        confirmText,
        cancelText,
        danger,
        checklist,
      });
    });
  };

  const handleConfirmAction = (confirmedChecks) => {
    confirmResolverRef.current?.(confirmModal.checklist.length ? confirmedChecks : true);
    confirmResolverRef.current = null;

    setConfirmModal((prev) => ({
      ...prev,
      open: false,
    }));
  };

  const handleCancelAction = () => {
    confirmResolverRef.current?.(false);
    confirmResolverRef.current = null;

    setConfirmModal((prev) => ({
      ...prev,
      open: false,
    }));
  };

  const toastTimerRef = useRef(null);

  const showToast = useCallback((
    message,
    type = 'success'
  ) => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
    }

    setToast({
      message,
      type,
    });

    toastTimerRef.current = setTimeout(() => {
      setToast({
        message: '',
        type: 'success',
      });
    }, 3500);
  }, []);

  const closeToast = () => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
    }

    setToast({
      message: '',
      type: 'success',
    });
  };

  const {
    token,
    user: authUser,
    authReady,
    loginError,
    login,
    logout,
  } = useAuth();

  const [
    selectedIpSegment,
    setSelectedIpSegment
  ] = useState('');

  const {
    search,
    setSearch,

    selectedDpto,
    setSelectedDpto,

    selectedEstadoIP,
    setSelectedEstadoIP,

    selectedEstadoAnexo,
    setSelectedEstadoAnexo,

    selectedEstadoGeneral,
    setSelectedEstadoGeneral,

    resetFilters,
  } = useModuleFilters();

  const {
    tab,

    sidebarOpen,
    openSidebar,
    closeSidebar,

    sidebarCollapsed,
    toggleSidebarCollapsed,

    selectTab,
  } = useModuleNavigation(resetFilters, authUser?.role);

  const isEquipmentModule = isEquipmentTab(tab);
  const equipmentCategory = getEquipmentCategoryByTab(tab);
  const activeModuleTab = getModuleTab(tab);

  const {
    editingItem,
    setEditingItem,

    newItem,
    setNewItem,

    selectedUser,
    setSelectedUser,

    historyEquipo,
    setHistoryEquipo,

    historyUsuario,
    setHistoryUsuario,

    historyAnexo,
    setHistoryAnexo,

    historyPCGenerico,
    setHistoryPCGenerico,

    historyServidor,
    setHistoryServidor,

    historyIp,
    setHistoryIp,

    historyPerfil,
    setHistoryPerfil,
  } = useModuleModals();

  const {
    dptosList,
    usuariosList,
    usuariosStats,
    ipsList,
    departamentosList,
    perfilesList,
    ipSegmentStats,
    refreshReferenceData,
    ensureReferenceData,
    invalidateReferenceData,
  } = useReferenceData(token, authUser?.role, activeModuleTab);

  const normalizedSearch = search.trim();
  const isGlobalUserSearch = (
    activeModuleTab === 'usuarios'
    && !selectedDpto
    && Boolean(normalizedSearch || selectedEstadoGeneral)
  );
  const isGlobalIpSearch = (
    activeModuleTab === 'ips'
    && !selectedIpSegment
    && Boolean(normalizedSearch)
  );

  const moduleDataEnabled = !(
    activeModuleTab === 'activos-resumen'
    || activeModuleTab === 'papelera'
    || (activeModuleTab === 'usuarios' && !selectedDpto && !normalizedSearch && !selectedEstadoGeneral)
    || (activeModuleTab === 'ips' && !selectedIpSegment && !normalizedSearch)
  );

  const {
    data,
    pagination,
    setPage,
    refreshData,
    getAllData,
    isLoading,
  } = useModuleData({
    token,
    tab: activeModuleTab,
    search,
    selectedDpto,
    equipmentCategory,
    selectedIpSegment,
    selectedEstadoIP,
    selectedEstadoAnexo,
    selectedEstadoGeneral,
    onUnauthorized: logout,
    enabled: moduleDataEnabled,
  });

  const refreshVisibleChanges = (modules) => {
    if (modules.includes(activeModuleTab)) refreshData();
    if (modules.includes('activos-resumen') && tab === 'activos-resumen') {
      setDashboardRevision((value) => value + 1);
    }
    if (modules.includes('equipos') && selectedEquipmentId) {
      setEquipmentDetailRevision((value) => value + 1);
    }
    const referenceSections = new Set();
    if (modules.includes(activeModuleTab)) {
      const primarySections = {
        usuarios: ['usuarios_stats'],
        ips: ['ips_stats'],
        perfiles: ['perfiles'],
        departamentos: ['departamentos'],
      }[activeModuleTab] || [];
      primarySections.forEach((section) => referenceSections.add(section));
    }
    if (modules.includes('departamentos') && ['usuarios', 'perfiles', 'pcs-genericos'].includes(activeModuleTab)) {
      referenceSections.add('departamentos');
    }
    if (modules.includes('usuarios') && ['equipos', 'anexos'].includes(activeModuleTab) && (newItem || editingItem)) {
      referenceSections.add('usuarios');
    }
    if (modules.includes('ips') && ['usuarios', 'servidores', 'pcs-genericos'].includes(activeModuleTab) && (newItem || editingItem)) {
      referenceSections.add('ips');
    }
    if (referenceSections.size) {
      refreshReferenceData([...referenceSections]);
    }
  };

  useRealtimeChanges({
    enabled: Boolean(token),
    onChanges: refreshVisibleChanges,
    onReconnect: () => refreshVisibleChanges([
      activeModuleTab,
      ...(tab === 'activos-resumen' ? ['activos-resumen'] : []),
    ]),
    onUnauthorized: logout,
  });

  const isViewer = authUser?.role === 'Visualizador';

  useIdleLogout({
    enabled: Boolean(token),
    timeoutMs: 5 * 60 * 1000,
    onActivity: async () => {
      try {
        await apiClient.post('/auth/activity/');
      } catch (error) {
        if (error.response?.status === 401) {
          await logout();
          showToast(
            'La sesión expiró por inactividad.',
            'error'
          );
        }
      }
    },
    onIdle: async () => {
      await logout();
      showToast(
        'Sesión cerrada por 5 minutos de inactividad.',
        'error'
      );
    },
  });

  const refreshAllData = async () => {
    if (activeModuleTab === 'departamentos') {
      invalidateReferenceData([
        'departamentos',
        'usuarios',
        'usuarios_stats',
        'perfiles',
      ]);
      await refreshData();
      return;
    }

    if (activeModuleTab === 'usuarios') {
      invalidateReferenceData(['usuarios']);
    }

    const referenceSections = {
      usuarios: ['usuarios_stats', 'ips'],
      equipos: ['usuarios'],
      anexos: ['usuarios'],
      ips: ['ips', 'ips_stats'],
      servidores: ['ips'],
      'pcs-genericos': ['ips'],
      perfiles: ['perfiles'],
    }[activeModuleTab] || [];

    const refreshTasks = [refreshData()];
    if (referenceSections.length > 0) {
      refreshTasks.push(refreshReferenceData(referenceSections));
    }

    await Promise.all(refreshTasks);
  };

  const {
    handleCreateSave,
    handleSave,
    handleDelete,
  } = useModuleCrud({
    tab: activeModuleTab,
    equipmentCategory,
    data,
    newItem,
    editingItem,
    setNewItem,
    setEditingItem,
    refreshAllData,
    showToast,
    requestConfirmation,
  });

  const handleLogin = async (e) => {
    e.preventDefault();

    const success = await login(
      username,
      password
    );

    if (success) {
      setPassword('');
    }
  };


  const handleLogout = async () => {
    const confirmed = await requestConfirmation({
      title: 'Cerrar sesión',
      message: '¿Confirmas que deseas cerrar la sesión actual?',
      confirmText: 'Cerrar sesión',
    });

    if (!confirmed) {
      return;
    }

    logout();

    showToast(
      'Sesión cerrada correctamente.',
      'success'
    );
  };

  const handleToggleProfileStatus = async (perfil) => {
    const isActive = perfil.estado !== 'INACTIVO';
    const nextStatus = isActive ? 'INACTIVO' : 'ACTIVO';

    const confirmed = await requestConfirmation({
      title: isActive ? 'Desactivar Perfil Genérico' : 'Reactivar Perfil Genérico',
      message: isActive
        ? `¿Confirmas que deseas desactivar "${perfil.nombre || perfil.usuario}"? El registro se conservará.`
        : `¿Confirmas que deseas reactivar "${perfil.nombre || perfil.usuario}"?`,
      confirmText: isActive ? 'Desactivar' : 'Reactivar',
      danger: isActive,
    });

    if (!confirmed) return;

    try {
      await updatePerfil(perfil.id, { estado: nextStatus });
      await refreshAllData();
      showToast(
        isActive
          ? 'Perfil Genérico desactivado correctamente.'
          : 'Perfil Genérico reactivado correctamente.',
        'success'
      );
    } catch (error) {
      console.error('Error actualizando estado del perfil:', error.response?.data || error);
      showToast('No se pudo actualizar el estado del Perfil Genérico.', 'error');
    }
  };


  const handleHostnameEquipoChange = (
    hostnameValue,
    targetState,
    setTargetState
  ) => {
    const nextState = buildEquipmentStateFromHostname(
      hostnameValue,
      targetState,
      usuariosList
    );

    setTargetState(nextState);
  };

  const handleIPInputChange = (
    value,
    targetState,
    setTargetState
  ) => {
    setTargetState({
      ...targetState,
      direccion_ip: sanitizeIpInput(value),
    });
  };

  const openDetailedItem = async (module, item, setter) => {
    try {
      const detailedItem = await getItemDetailsByTab(module, item.id);
      setter(detailedItem);
    } catch (error) {
      console.error('Error cargando detalle:', error.response?.data || error);
      showToast('No se pudo cargar el detalle solicitado.', 'error');
    }
  };

  const openDashboardAssetForEdit = async (item) => {
    if (authUser?.role === 'Visualizador') return;
    const category = {
      Notebook: 'equipos-notebook', Celular: 'equipos-celular', Tablet: 'equipos-tablet',
      Mac: 'equipos-mac', 'BAM / Router': 'equipos-bam-router',
    }[item.tipo] || 'equipos-perifericos';
    selectTab(category);
    try {
      await ensureReferenceData(['usuarios']);
      const detail = await getItemDetailsByTab('equipos', item.id);
      setEditingItem(detail);
    } catch {
      showToast('No se pudo abrir el equipo.', 'error');
    }
  };

  const openIpHistory = async (ip) => {
    try {
      const historial = await getIpAssignmentHistory(ip.id);
      setHistoryIp({ ...ip, historial });
    } catch (error) {
      console.error('Error cargando historial IP:', error.response?.data || error);
      showToast('No se pudo cargar el historial de la IP.', 'error');
    }
  };

  const getFormReferenceSections = () => ({
    usuarios: ['ips'],
    equipos: ['usuarios'],
    anexos: ['usuarios'],
    'pcs-genericos': ['ips'],
    servidores: ['ips'],
  })[activeModuleTab] || [];

  const loadFormReferences = async () => {
    const sections = getFormReferenceSections();
    if (sections.length > 0) {
      await ensureReferenceData(sections);
    }
  };

  const handleOpenCreateModal = async () => {
    if (isViewer) {
      return;
    }

    await loadFormReferences();

    const initialItem = getInitialCreateItem(activeModuleTab);

    if (isEquipmentModule && initialItem) {
      initialItem.tipo = equipmentCategory === 'PERIFERICOS'
        ? 'Monitor'
        : equipmentCategory;
    }

    setNewItem(initialItem);
  };

  const handleOpenEditModal = async (item) => {
    if (isViewer) {
      return;
    }

    await loadFormReferences();
    setEditingItem(item);
  };

  const filteredData = data;

  const handleExportUsuarios = async () => {
    try {
      const rows = await getAllData();
      await exportUsuariosExcel({
        rows,
        selectedDpto,
      });

      showToast(
        selectedDpto
          ? `Excel del área ${selectedDepartmentLabel} exportado correctamente.`
          : 'Excel general de usuarios exportado correctamente.',
        'success'
      );
    } catch (error) {
      showToast(
        error.message ||
        'No se pudo exportar el archivo Excel.',
        'error'
      );
    }
  };

  const handleExportEquipos = async () => {
    try {
      const rows = await getAllData();
      await exportEquiposExcel({
        rows,
        selectedCategoriaEquipo: equipmentCategory,
      });

      showToast(
        equipmentCategory
          ? `Excel de ${selectedEquipmentLabel} exportado correctamente.`
          : 'Excel general de equipos exportado correctamente.',
        'success'
      );
    } catch (error) {
      showToast(
        error.message ||
        'No se pudo exportar el archivo Excel.',
        'error'
      );
    }
  };

  const handleExportIps = async () => {
    try {
      const rows = await getAllData();
      await exportIpsExcel({
        rows,
        selectedIpSegment,
      });

      showToast(
        selectedIpSegment
          ? `Excel del segmento ${selectedIpSegmentLabel} exportado correctamente.`
          : 'Excel general de IPs exportado correctamente.',
        'success'
      );
    } catch (error) {
      showToast(
        error.message ||
        'No se pudo exportar el archivo Excel.',
        'error'
      );
    }
  };

  const handleExportServidores = async () => {
    try {
      const rows = await getAllData();
      await exportServidoresExcel({
        rows,
      });

      showToast(
        'Excel de servidores exportado correctamente.',
        'success'
      );
    } catch (error) {
      showToast(
        error.message ||
        'No se pudo exportar el archivo Excel.',
        'error'
      );
    }
  };

  const handleExportPerfiles = async () => {
    try {
      const rows = await getAllData();
      await exportPerfilesExcel({
        rows,
        selectedDpto: selectedProfileFilterLabel,
      });

      showToast(
        selectedProfileFilterLabel
          ? `Excel de perfiles de ${selectedProfileFilterLabel} exportado correctamente.`
          : 'Excel general de perfiles exportado correctamente.',
        'success'
      );
    } catch (error) {
      showToast(
        error.message ||
        'No se pudo exportar el archivo Excel.',
        'error'
      );
    }
  };

  const handleExportAnexos = async () => {
    try {
      const rows = await getAllData();
      await exportAnexosExcel({
        rows,
      });

      showToast(
        'Excel de anexos exportado correctamente.',
        'success'
      );
    } catch (error) {
      showToast(
        error.message ||
        'No se pudo exportar el archivo Excel.',
        'error'
      );
    }
  };

  const handleExportPCsGenericos = async () => {
    try {
      const rows = await getAllData();
      await exportPCsGenericosExcel({
        rows,
        selectedDpto,
      });

      showToast(
        selectedDpto
          ? `Excel de PCs Genéricos del área ${selectedDpto} exportado correctamente.`
          : 'Excel general de PCs Genéricos exportado correctamente.',
        'success'
      );
    } catch (error) {
      showToast(
        error.message ||
        'No se pudo exportar el archivo Excel.',
        'error'
      );
    }
  };
  const equipmentResultsRef = useRef(null);
  const userResultsRef = useRef(null);
  const ipResultsRef = useRef(null);

  const getDepartmentDisplayLabel = (department) => {
    if (!department) {
      return '';
    }

    const normalizedDepartment =
      department.trim().toLowerCase();

    if (
      normalizedDepartment === 'infraestructura ti' ||
      normalizedDepartment === 'ti'
    ) {
      return 'TECNOLOGÍA';
    }

    return department;
  };

  const selectedDepartmentLabel =
    getDepartmentDisplayLabel(selectedDpto);

  const getProfileFilterLabel = (filterValue) => {
    if (!filterValue) return '';

    if (filterValue.startsWith('dept:')) {
      const id = Number(filterValue.split(':')[1]);
      return departamentosList.find((department) => Number(department.id) === id)?.nombre || '';
    }

    if (filterValue.startsWith('subarea:')) {
      const id = Number(filterValue.split(':')[1]);
      for (const department of departamentosList) {
        const subarea = (department.subareas || []).find(
          (item) => Number(item.id) === id
        );
        if (subarea) return `${department.nombre} / ${subarea.nombre}`;
      }
      return '';
    }

    return getDepartmentDisplayLabel(filterValue);
  };

  const selectedProfileFilterLabel =
    tab === 'perfiles' ? getProfileFilterLabel(selectedDpto) : '';

  useEffect(() => {
    if (
      tab === 'usuarios' &&
      selectedDpto &&
      userResultsRef.current
    ) {
      const timeout = setTimeout(() => {
        userResultsRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      }, 100);

      return () => clearTimeout(timeout);
    }
  }, [tab, selectedDpto]);

  const selectedEquipmentLabel = getEquipmentLabelByTab(tab);

  const selectedIpSegmentData =
    IP_SEGMENTS.find(
      (segment) =>
        segment.id === selectedIpSegment
    );

  const selectedIpSegmentLabel =
    selectedIpSegmentData?.label || '';

  /* =========================
     SCROLL RESULTADOS EQUIPOS
  ========================= */

  useEffect(() => {
    if (
      isEquipmentModule &&
      equipmentResultsRef.current
    ) {
      const timeout = setTimeout(() => {
        equipmentResultsRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      }, 100);

      return () => clearTimeout(timeout);
    }
  }, [tab, isEquipmentModule]);


  /* =========================
     SCROLL RESULTADOS IPS
  ========================= */

  useEffect(() => {
    if (
      tab === 'ips' &&
      selectedIpSegment &&
      ipResultsRef.current
    ) {
      const timeout = setTimeout(() => {
        ipResultsRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      }, 100);

      return () => clearTimeout(timeout);
    }
  }, [tab, selectedIpSegment]);


  /* =========================
     IPS DISPONIBLES USUARIO
  ========================= */

  const availableIpsForUser = (currentIp) => {
    return getAvailableIpsForUser(
      ipsList,
      currentIp
    );
  };

  const handleSelectTab = (selectedTab) => {
    setSelectedIpSegment('');
    selectTab(selectedTab);
  };

  if (!authReady) { return null; }

  if (!token) {
    return (
      <>
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={closeToast}
        />

        <LoginPage
          username={username}
          password={password}
          loginError={loginError}
          onUsernameChange={setUsername}
          onPasswordChange={setPassword}
          onSubmit={handleLogin}
        />
      </>
    );
  }

  return (

    <div className="app-shell">
      <Toast
        message={toast.message}
        type={toast.type}
        onClose={closeToast}
      />

      {confirmModal.open && <ConfirmModal
        open={confirmModal.open}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmText={confirmModal.confirmText}
        cancelText={confirmModal.cancelText}
        danger={confirmModal.danger}
        checklist={confirmModal.checklist}
        onConfirm={handleConfirmAction}
        onCancel={handleCancelAction}
      />}
      {secretRequest && (
        <SecretRevealModal
          request={secretRequest}
          username={authUser?.username || ''}
          onClose={() => setSecretRequest(null)}
        />
      )}
      {/* SIDEBAR */}
      <Sidebar
        isOpen={sidebarOpen}
        collapsed={sidebarCollapsed}
        activeTab={tab}
        onClose={closeSidebar}
        onToggleCollapse={toggleSidebarCollapsed}
        onSelectTab={handleSelectTab}
        onLogout={handleLogout}
        role={authUser?.role}
      />



      {/* CONTENIDO PRINCIPAL */}
      <main
        className={`app-main ${sidebarCollapsed
          ? 'app-main-sidebar-collapsed'
          : ''
          }`}
      >
        {/* ENCABEZADO */}
        <Header
          activeTab={tab}
          role={authUser?.role}
          onOpenSidebar={openSidebar}
        />

        {/* FILTROS Y ACCIONES */}
        {/* CATEGORÍAS DE EQUIPOS */}

        {/* ACCIONES DE EQUIPOS SIN CATEGORÍA SELECCIONADA */}

        {/* ÁREAS DE USUARIOS */}
        {tab === 'usuarios' && (
          <UserDepartmentCards
            stats={usuariosStats}
            selectedDepartment={selectedDpto}
            onSelectDepartment={setSelectedDpto}
          />
        )}

        {tab === 'perfiles' && (
          <PerfilDepartmentCards
            perfiles={perfilesList}
            departamentos={departamentosList}
            selectedFilter={selectedDpto}
            onSelectFilter={setSelectedDpto}
          />
        )}

        {/* ACCIONES DE USUARIOS SIN ÁREA SELECCIONADA */}
        {tab === 'usuarios' && !selectedDpto && (
          <ModuleToolbar
            activeTab={tab}
            selectedGeneralStatus={selectedEstadoGeneral}
            onGeneralStatusChange={setSelectedEstadoGeneral}
            readOnly={isViewer}
            departments={dptosList}

            selectedDepartment={selectedDpto}
            onDepartmentChange={setSelectedDpto}

            selectedIpStatus={selectedEstadoIP}
            onIpStatusChange={setSelectedEstadoIP}

            selectedAnexoStatus={
              selectedEstadoAnexo
            }
            onAnexoStatusChange={
              setSelectedEstadoAnexo
            }

            search={search}
            onSearchChange={setSearch}
            searching={isLoading && Boolean(normalizedSearch)}
            onCreate={handleOpenCreateModal}

            onExport={
              tab === 'usuarios'
                ? handleExportUsuarios
                : undefined
            }
          />
        )}




        {/* SEGMENTOS DE IP */}
        {tab === 'ips' && (
          <IpSegmentCards
            segmentStats={ipSegmentStats}
            selectedSegment={selectedIpSegment}
            onSelectSegment={setSelectedIpSegment}
          />
        )}

        {/* ACCIONES DE IPS SIN SEGMENTO SELECCIONADO */}
        {tab === 'ips' && !selectedIpSegment && (
          <ModuleToolbar
            activeTab={tab}
            readOnly={isViewer}
            departments={dptosList}

            selectedDepartment={selectedDpto}
            onDepartmentChange={setSelectedDpto}

            selectedIpStatus={selectedEstadoIP}
            onIpStatusChange={setSelectedEstadoIP}

            selectedAnexoStatus={selectedEstadoAnexo}
                  onAnexoStatusChange={setSelectedEstadoAnexo}
                  selectedGeneralStatus={selectedEstadoGeneral}
                  onGeneralStatusChange={setSelectedEstadoGeneral}

            search={search}
            onSearchChange={setSearch}
            searching={isLoading && Boolean(normalizedSearch)}
            onCreate={handleOpenCreateModal}
            onExport={handleExportIps}
          />
        )}

        {tab === 'activos-resumen' && <AssetDashboard revision={dashboardRevision} onOpenAsset={(item) => setSelectedEquipmentId(item.id)} onEditAsset={openDashboardAssetForEdit} />}

        {tab === 'papelera' && authUser?.role === 'Administrador' && (
          <PapeleraPage requestConfirmation={requestConfirmation} showToast={showToast} />
        )}

        {tab === 'departamentos' && (
          <DepartamentosSubareasPage
            departamentos={data}
            onRefresh={refreshAllData}
            showToast={showToast}
            requestConfirmation={requestConfirmation}
            role={authUser?.role}
          />
        )}

        {/* RESULTADOS DEL MÓDULO */}
        {(
          isEquipmentModule ||
          (tab === 'usuarios' && selectedDpto) ||
          isGlobalUserSearch ||
          (tab === 'ips' && selectedIpSegment) ||
          isGlobalIpSearch ||
          (
            !isEquipmentModule &&
            tab !== 'usuarios' &&
            tab !== 'ips' &&
            tab !== 'departamentos' &&
            tab !== 'activos-resumen'
            && tab !== 'papelera'
          )
        ) && (
            <>
              {/* ENCABEZADO DEL RESULTADO DE EQUIPOS */}
              {isEquipmentModule && (
                <div
                  ref={equipmentResultsRef}
                  className="equipment-results-header"
                >
                  <div>
                    <span className="equipment-results-eyebrow">
                      Categoría seleccionada
                    </span>

                    <h2>
                      {selectedEquipmentLabel}
                    </h2>
                  </div>

                  <div className="equipment-results-count">
                    <strong>
                      {pagination.count}
                    </strong>

                    <span>
                      {pagination.count === 1
                        ? ' equipo'
                        : ' equipos'}
                    </span>
                  </div>
                </div>
              )}

              {/* ENCABEZADO DEL RESULTADO DE USUARIOS */}
              {tab === 'usuarios' && (
                <div
                  ref={userResultsRef}
                  className="equipment-results-header"
                >
                  <div>
                    <span className="equipment-results-eyebrow">
                      {isGlobalUserSearch
                        ? 'Consulta global de usuarios'
                        : 'Departamento / Área seleccionada'}
                    </span>

                    <h2>
                      {isGlobalUserSearch
                        ? (normalizedSearch ? `Resultados para "${normalizedSearch}"` : 'Usuarios por estado')
                        : selectedDepartmentLabel}
                    </h2>
                  </div>

                  <div className="equipment-results-count">
                    <strong>
                      {pagination.count}
                    </strong>

                    <span>
                      {pagination.count === 1
                        ? ' usuario'
                        : ' usuarios'}
                    </span>
                  </div>
                </div>
              )}

              {/* ENCABEZADO DEL RESULTADO DE IPS */}
              {tab === 'ips' && (
                <div
                  ref={ipResultsRef}
                  className="equipment-results-header"
                >
                  <div>
                    <span className="equipment-results-eyebrow">
                      {isGlobalIpSearch
                        ? 'Búsqueda global de direcciones IP'
                        : 'Segmento seleccionado'}
                    </span>

                    <h2>
                      {isGlobalIpSearch
                        ? `Resultados para "${normalizedSearch}"`
                        : selectedIpSegmentLabel}
                    </h2>
                  </div>

                  <div className="equipment-results-count">
                    <strong>
                      {pagination.count}
                    </strong>

                    <span>
                      {pagination.count === 1
                        ? ' IP'
                        : ' IPs'}
                    </span>
                  </div>
                </div>
              )}
              {/* FILTROS Y ACCIONES */}
              {!isGlobalUserSearch && !isGlobalIpSearch && (
                <ModuleToolbar
                  activeTab={activeModuleTab}
                  readOnly={isViewer}
                  departments={dptosList}
                  equipmentDepartments={departamentosList}

                  selectedDepartment={selectedDpto}
                  onDepartmentChange={setSelectedDpto}

                  selectedIpStatus={selectedEstadoIP}
                  onIpStatusChange={setSelectedEstadoIP}

                  selectedAnexoStatus={
                    selectedEstadoAnexo
                  }
                  onAnexoStatusChange={
                    setSelectedEstadoAnexo
                  }
                  selectedGeneralStatus={selectedEstadoGeneral}
                  onGeneralStatusChange={setSelectedEstadoGeneral}
                  search={search}
                  onSearchChange={setSearch}
                  searching={isLoading && Boolean(normalizedSearch)}
                  onCreate={handleOpenCreateModal}

                  onExport={
                    tab === 'usuarios'
                      ? handleExportUsuarios
                      : isEquipmentModule
                        ? handleExportEquipos
                        : tab === 'ips'
                          ? handleExportIps
                          : tab === 'servidores'
                            ? handleExportServidores
                            : tab === 'perfiles'
                              ? handleExportPerfiles
                              : tab === 'anexos'
                                ? handleExportAnexos
                                : tab === 'pcs-genericos'
                                  ? handleExportPCsGenericos
                                  : undefined
                  }
                />
              )}

              {/* TABLA PRINCIPAL */}
              <div className="app-table-container">
                <ModuleTable
                  tab={activeModuleTab}
                  data={filteredData}

                  formatEquipmentType={
                    formatEquipmentType
                  }

                  renderUsuarioStatusBadge={
                    renderUsuarioStatusBadge
                  }

                  renderAccountTypeBadge={
                    renderAccountTypeBadge
                  }

                  renderIpStatusBadge={
                    renderIpStatusBadge
                  }

                  renderAnexoStatusBadge={
                    renderAnexoStatusBadge
                  }

                  onSelectUser={
                    (item) => openDetailedItem('usuarios', item, setSelectedUser)
                  }

                  onShowUserHistory={
                    (item) => openDetailedItem('usuarios', item, setHistoryUsuario)
                  }

                  onShowEquipmentHistory={
                    (item) => openDetailedItem('equipos', item, setHistoryEquipo)
                  }
                  onSelectEquipment={(item) => setSelectedEquipmentId(item.id)}

                  onShowIpHistory={openIpHistory}

                  onShowProfileHistory={
                    (item) => openDetailedItem('perfiles', item, setHistoryPerfil)
                  }

                  onShowAnexoHistory={
                    (item) => openDetailedItem('anexos', item, setHistoryAnexo)
                  }

                  onShowPCGenericoHistory={
                    (item) => openDetailedItem('pcs-genericos', item, setHistoryPCGenerico)
                  }

                  onShowServidorHistory={
                    (item) => openDetailedItem('servidores', item, setHistoryServidor)
                  }

                  onEdit={
                    handleOpenEditModal
                  }

                  onDelete={handleDelete}
                  onToggleProfileStatus={handleToggleProfileStatus}
                  role={authUser?.role}
                  onRevealSecret={setSecretRequest}
                />
              </div>

              <Pagination
                page={pagination.page}
                totalPages={pagination.totalPages}
                count={pagination.count}
                pageSize={pagination.pageSize}
                onPageChange={setPage}
              />
            </>
          )}

        {(selectedEquipmentId || legacyQrToken) && <EquipoDetailModal
          key={selectedEquipmentId || legacyQrToken}
          id={selectedEquipmentId}
          revision={equipmentDetailRevision}
          token={legacyQrToken}
          onClose={() => {
            setSelectedEquipmentId(null);
            setLegacyQrToken(null);
            if (window.location.pathname.startsWith('/qr/a/')) window.history.replaceState(null, '', '/');
          }}
          onOpenHistory={(equipo) => {
            setSelectedEquipmentId(null);
            setLegacyQrToken(null);
            if (window.location.pathname.startsWith('/qr/a/')) window.history.replaceState(null, '', '/');
            openDetailedItem('equipos', equipo, setHistoryEquipo);
          }} />}

        {/* MODALES DE DETALLE / HISTORIAL */}
        <ModuleDetailModals
          role={authUser?.role}
          onRevealSecret={setSecretRequest}
          selectedUser={
            selectedUser
          }

          historyUsuario={
            historyUsuario
          }

          historyEquipo={
            historyEquipo
          }

          historyAnexo={
            historyAnexo
          }

          historyPCGenerico={
            historyPCGenerico
          }

          historyServidor={
            historyServidor
          }

          historyIp={
            historyIp
          }

          historyPerfil={
            historyPerfil
          }

          onCloseUser={() =>
            setSelectedUser(null)
          }

          onCloseUserHistory={() =>
            setHistoryUsuario(null)
          }

          onCloseEquipmentHistory={() =>
            setHistoryEquipo(null)
          }

          onCloseAnexoHistory={() =>
            setHistoryAnexo(null)
          }

          onClosePCGenericoHistory={() =>
            setHistoryPCGenerico(null)
          }

          onCloseServidorHistory={() =>
            setHistoryServidor(null)
          }

          onCloseIpHistory={() =>
            setHistoryIp(null)
          }

          onCloseProfileHistory={() =>
            setHistoryPerfil(null)
          }

          renderUsuarioStatusBadge={
            renderUsuarioStatusBadge
          }

          formatEquipmentType={
            formatEquipmentType
          }
        />

        {/* CREAR */}
        {!isViewer && (
        <ModuleCreateModal
          tab={activeModuleTab}
          equipmentCategory={equipmentCategory}
          newItem={newItem}
          setNewItem={setNewItem}

          onSubmit={
            handleCreateSave
          }

          onClose={() =>
            setNewItem(null)
          }

          departmentCatalog={
            departamentosList
          }

          usuarios={
            usuariosList
          }

          availableIps={
            tab === 'servidores'
              ? getAvailableIpsForServer(ipsList, newItem?.ip)
              : availableIpsForUser(newItem?.ip_seleccionada)
          }

          formatEquipmentType={
            formatEquipmentType
          }

          onHostnameChange={(value) =>
            handleHostnameEquipoChange(
              value,
              newItem,
              setNewItem
            )
          }

          onIpChange={(value) =>
            handleIPInputChange(
              value,
              newItem,
              setNewItem
            )
          }
        />
        )}

        {/* EDITAR */}
        {!isViewer && (
        <ModuleEditModal
          tab={activeModuleTab}
          equipmentCategory={equipmentCategory}

          editingItem={
            editingItem
          }

          setEditingItem={
            setEditingItem
          }

          onSubmit={
            handleSave
          }

          onClose={() =>
            setEditingItem(null)
          }

          departmentCatalog={
            departamentosList
          }

          usuarios={
            usuariosList
          }

          availableIps={
            tab === 'servidores'
              ? getAvailableIpsForServer(ipsList, editingItem?.ip)
              : availableIpsForUser(editingItem?.ip_actual)
          }

          formatEquipmentType={
            formatEquipmentType
          }

          onHostnameChange={(value) =>
            handleHostnameEquipoChange(
              value,
              editingItem,
              setEditingItem
            )
          }

          onIpChange={(value) =>
            handleIPInputChange(
              value,
              editingItem,
              setEditingItem
            )
          }
        />
        )}
      </main>
    </div>
  );
}
