import { Bell, Menu } from 'lucide-react';

import './Header.css';
import {
  getEquipmentLabelByTab,
  isEquipmentTab,
} from '../../utils/equipmentNavigation';

export default function Header({
  activeTab,
  role,
  onOpenSidebar,
  onOpenNotifications,
  pendingReviewCount = 0,
}) {
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
    <header className="main-header">
      <div className="main-header-left">
        {/* Solo visible en tablet / móvil */}
        <button
          type="button"
          onClick={onOpenSidebar}
          className="header-menu-button"
          title="Abrir menú de módulos"
          aria-label="Abrir menú de módulos"
        >
          <Menu size={21} />
        </button>

        <div className="main-header-titles">
          <h1>
            Portal de Infraestructura TI Chile
          </h1>

          <div className="main-header-module">
            {getTitle()}
          </div>

          <p>
            {role === 'Visualizador'
              ? 'Vista de consulta de Anexos'
              : 'Panel Administrador de Infraestructura y Redes'}
          </p>
        </div>
      </div>

      {role !== 'Visualizador' && (
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
      )}

    </header>
  );
}
