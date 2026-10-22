import { Bell, ChevronDown, LogOut, Menu } from 'lucide-react';

import './Header.css';
import {
  getEquipmentLabelByTab,
  isEquipmentTab,
} from '../../utils/equipmentNavigation';

export default function Header({
  activeTab,
  role,
  username,
  displayName,
  onOpenSidebar,
  onOpenNotifications,
  onLogout,
  pendingReviewCount = 0,
}) {
  const isViewer = role === 'Visualizador';
  const sessionName = displayName || username || 'Usuario';
  const initials = sessionName
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toLocaleUpperCase('es-CL');
  const accountMenu = (
    <details className="header-account">
      <summary aria-label={`Cuenta de ${sessionName}`}>
        <span className="header-account-avatar" aria-hidden="true">{initials}</span>
        <span className="header-account-copy"><strong>{sessionName}</strong><small>{role}</small></span>
        <ChevronDown size={15} aria-hidden="true" />
      </summary>
      <div className="header-account-menu">
        <button type="button" onClick={onLogout}><LogOut size={16} aria-hidden="true" /> Cerrar sesión</button>
      </div>
    </details>
  );
  const getTitle = () => {
    if (isEquipmentTab(activeTab)) {
      return `Equipos / ${getEquipmentLabelByTab(activeTab)}`;
    }

    switch (activeTab) {
      case 'usuarios':
        return 'Usuarios';

      case 'equipos':
        return 'Equipos';

      case 'activos-resumen':
        return 'Equipos / Tablero de activos';

      case 'revisiones-baja':
        return 'Notificaciones / Recursos por revisar';

      case 'pcs-genericos':
        return 'PCs Genéricos';

      case 'servidores':
        return 'Servidores';

      case 'perfiles':
        return 'Perfiles Genéricos';

      case 'ips':
        return 'Gestión de IPs';

      case 'anexos':
        return 'Anexos';

      case 'departamentos':
        return 'Departamentos / Áreas';

      default:
        return 'Portal de Infraestructura TI Chile';
    }
  };

  return (
    <header className={`main-header ${isViewer ? 'main-header-viewer' : ''}`}>
      <div className="main-header-left">
        {isViewer ? (
          <img
            className="header-viewer-logo"
            src="/branding/dr-simi-logo.png"
            alt="Farmacias del Dr. Simi"
          />
        ) : (
          <button
            type="button"
            onClick={onOpenSidebar}
            className="header-menu-button"
            title="Abrir menú de módulos"
            aria-label="Abrir menú de módulos"
          >
            <Menu size={21} />
          </button>
        )}

        <div className="main-header-titles">
          <h1>
            Portal de Infraestructura TI Chile
          </h1>

          <div className="main-header-module">
            {getTitle()}
          </div>

          <p>
            {isViewer
              ? 'Consulta de anexos asignados'
              : 'Panel Administrador de Infraestructura y Redes'}
          </p>
        </div>
      </div>

      {isViewer ? (
        accountMenu
      ) : (
        <div className="header-actions">
          <button
            type="button"
            className={`header-notifications-button ${activeTab === 'revisiones-baja' ? 'is-active' : ''}`}
            onClick={onOpenNotifications}
            aria-label={`Notificaciones: ${pendingReviewCount} ${pendingReviewCount === 1 ? 'liberación pendiente' : 'liberaciones pendientes'}`}
            aria-current={activeTab === 'revisiones-baja' ? 'page' : undefined}
            title="Ver notificaciones de recursos liberados"
          >
            <Bell size={21} aria-hidden="true" />
            {pendingReviewCount > 0 && <span className="header-notifications-count" aria-hidden="true">{pendingReviewCount > 99 ? '99+' : pendingReviewCount}</span>}
          </button>
          {accountMenu}
        </div>
      )}

    </header>
  );
}
