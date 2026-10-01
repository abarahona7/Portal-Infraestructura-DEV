import { useState } from 'react';

import {
  X,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Users,
  Package,
  BarChart3,
  Monitor,
  Laptop,
  Smartphone,
  Tablet,
  Wifi,
  Keyboard,
  Server,
  Mail,
  Globe2,
  Phone,
  Building2,
} from 'lucide-react';

import './Sidebar.css';

const GROUPS_KEY = 'portal-infra-ti-chile-sidebar-groups';

const navigationGroups = [
  {
    id: 'usuarios-group',
    parent: {
      id: 'usuarios',
      icon: Users,
      label: 'Usuarios',
    },
    children: [
      {
        id: 'anexos',
        icon: Phone,
        label: 'Anexos',
      },
      {
        id: 'perfiles',
        icon: Mail,
        label: 'Perfiles Genéricos',
      },
      {
        id: 'departamentos',
        icon: Building2,
        label: 'Departamentos / Áreas',
      },
    ],
  },
  {
    id: 'equipos-group',
    parent: {
      id: 'equipos',
      icon: Package,
      label: 'Equipos',
    },
    children: [
      {
        id: 'activos-resumen',
        icon: BarChart3,
        label: 'Tablero de Activos',
      },
      {
        id: 'pcs-genericos',
        icon: Monitor,
        label: 'PCs Genéricos',
      },
      {
        id: 'equipos-notebook',
        icon: Laptop,
        label: 'Notebook',
      },
      {
        id: 'equipos-celular',
        icon: Smartphone,
        label: 'Celular',
      },
      {
        id: 'equipos-tablet',
        icon: Tablet,
        label: 'Tablet',
      },
      {
        id: 'equipos-mac',
        icon: Monitor,
        label: 'Mac',
      },
      {
        id: 'equipos-bam-router',
        icon: Wifi,
        label: 'BAM / Router',
      },
      {
        id: 'equipos-perifericos',
        icon: Keyboard,
        label: 'Periféricos',
      },
    ],
  },
  {
    id: 'ips-group',
    parent: {
      id: 'ips',
      icon: Globe2,
      label: 'Gestión de IPs',
    },
    children: [
      {
        id: 'servidores',
        icon: Server,
        label: 'Servidores',
      },
    ],
  },
];

const readSavedGroups = () => {
  try {
    const rawValue = sessionStorage.getItem(GROUPS_KEY);

    if (!rawValue) {
      return {};
    }

    const parsed = JSON.parse(rawValue);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
};

const saveGroups = (groups) => {
  try {
    sessionStorage.setItem(GROUPS_KEY, JSON.stringify(groups));
  } catch {
    // La navegación sigue funcionando aunque sessionStorage no esté disponible.
  }
};

export default function Sidebar({
  isOpen,
  collapsed,
  activeTab,
  activeCount,
  onClose,
  onToggleCollapse,
  onSelectTab,
  role,
}) {
  const [openGroups, setOpenGroups] = useState(readSavedGroups);

  const toggleGroup = (groupId) => {
    setOpenGroups((current) => {
      const next = {
        ...current,
        [groupId]: !current[groupId],
      };

      saveGroups(next);
      return next;
    });
  };

  const showGroup = (groupId) => {
    setOpenGroups((current) => {
      if (current[groupId]) return current;
      const next = { ...current, [groupId]: true };
      saveGroups(next);
      return next;
    });
  };

  const groupContainsActiveTab = (group) => (
    group.parent.id === activeTab ||
    group.children.some((child) => child.id === activeTab)
  );

  const isGroupOpen = (group) => {
    if (collapsed) {
      return false;
    }

    if (Object.prototype.hasOwnProperty.call(openGroups, group.id)) {
      return Boolean(openGroups[group.id]);
    }

    return groupContainsActiveTab(group);
  };

  const renderModuleButton = (module, { child = false } = {}) => {
    const active = activeTab === module.id;
    const Icon = module.icon;

    return (
      <button
        key={module.id}
        type="button"
        className={[
          child ? 'sidebar-child-button' : 'sidebar-module-button',
          active ? 'sidebar-module-active' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        onClick={() => onSelectTab(module.id)}
        title={collapsed ? module.label : undefined}
      >
        <span className="sidebar-module-icon">
          <Icon size={child ? 16 : 18} />
        </span>

        <span className="sidebar-module-content">
          <span className="sidebar-module-label">
            {module.label}
          </span>

          {active && activeCount !== undefined && (
            <span className="sidebar-module-count">
              {activeCount}
            </span>
          )}
        </span>
      </button>
    );
  };

  return (
    <>
      <div
        className={`sidebar-overlay ${
          isOpen ? 'sidebar-overlay-open' : ''
        }`}
        onClick={onClose}
      />

      <aside
        className={[
          'sidebar',
          collapsed ? 'sidebar-collapsed' : '',
          isOpen ? 'sidebar-mobile-open' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <div className="sidebar-logo">
              <img
                src="/branding/dr-simi-logo.png"
                alt="FARMACIAS DEL DR. SIMI"
              />
            </div>

            {!collapsed && (
              <div className="sidebar-brand-text">
                <h2>TI Chile</h2>
                <span>Infraestructura</span>
              </div>
            )}
          </div>

          <button
            type="button"
            className="sidebar-collapse-button"
            onClick={onToggleCollapse}
            title={collapsed ? 'Expandir menú' : 'Contraer menú'}
            aria-label={collapsed ? 'Expandir menú' : 'Contraer menú'}
          >
            {collapsed ? (
              <ChevronRight size={18} />
            ) : (
              <ChevronLeft size={18} />
            )}
          </button>

          <button
            type="button"
            className="sidebar-mobile-close"
            onClick={onClose}
            title="Cerrar menú"
            aria-label="Cerrar menú"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {role === 'Visualizador' ? (
            renderModuleButton({
              id: 'anexos',
              icon: Phone,
              label: 'Anexos',
            })
          ) : (
            navigationGroups.map((group) => {
              const expanded = isGroupOpen(group);
              const groupActive = groupContainsActiveTab(group);
              const ParentIcon = group.parent.icon;

              return (
                <div
                  key={group.id}
                  className={`sidebar-group ${groupActive ? 'sidebar-group-active' : ''}`}
                >
                  <div className="sidebar-group-row">
                    <button
                      type="button"
                      className={`sidebar-module-button sidebar-group-parent ${
                        activeTab === group.parent.id
                          ? 'sidebar-module-active'
                          : ''
                      }`}
                      onClick={() => { if (group.id === 'equipos-group') showGroup(group.id); onSelectTab(group.parent.id); }}
                      title={collapsed ? group.parent.label : undefined}
                    >
                      <span className="sidebar-module-icon">
                        <ParentIcon size={18} />
                      </span>

                      <span className="sidebar-module-content">
                        <span className="sidebar-module-label">
                          {group.parent.label}
                        </span>

                        {activeTab === group.parent.id &&
                          activeCount !== undefined && (
                            <span className="sidebar-module-count">
                              {activeCount}
                            </span>
                          )}
                      </span>
                    </button>

                    {!collapsed && (
                      <button
                        type="button"
                        className={`sidebar-group-toggle ${
                          expanded ? 'is-open' : ''
                        }`}
                        onClick={() => toggleGroup(group.id)}
                        title={expanded ? 'Contraer grupo' : 'Expandir grupo'}
                        aria-label={`${expanded ? 'Contraer' : 'Expandir'} ${group.parent.label}`}
                        aria-expanded={expanded}
                      >
                        <ChevronDown size={16} />
                      </button>
                    )}
                  </div>

                  {expanded && (
                    <div className="sidebar-children">
                      {group.children.map((child) => (
                        <div key={child.id}>
                          {renderModuleButton(child, { child: true })}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </nav>

        <div className="sidebar-footer">
          {collapsed ? (
            <span
              className="sidebar-footer-mini"
              title="FARMACIAS DEL DR. SIMI"
            >
              TI
            </span>
          ) : (
            <>
              <strong>FARMACIAS DEL DR. SIMI</strong>
              <span>Infraestructura TI</span>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
