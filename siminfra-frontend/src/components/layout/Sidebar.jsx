import {
  X,
  ChevronLeft,
  ChevronRight,
  Users,
  Package,
  Monitor,
  Server,
  Mail,
  Globe2,
  Phone,
} from 'lucide-react';

import './Sidebar.css';

const modules = [
  {
    id: 'usuarios',
    icon: Users,
    label: 'Usuarios',
  },
  {
    id: 'equipos',
    icon: Package,
    label: 'Equipos',
  },
  {
    id: 'pcs-genericos',
    icon: Monitor,
    label: 'PCs Genéricos',
  },
  {
    id: 'servidores',
    icon: Server,
    label: 'Servidores',
  },
  {
    id: 'perfiles',
    icon: Mail,
    label: 'Perfiles Genéricos',
  },
  {
    id: 'ips',
    icon: Globe2,
    label: 'Gestión de IPs',
  },
  {
    id: 'anexos',
    icon: Phone,
    label: 'Anexos',
  },
];

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
                alt="Farmacias Dr. Simi"
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
            title={
              collapsed
                ? 'Expandir menú'
                : 'Contraer menú'
            }
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
          >
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {modules
            .filter((module) =>
              role === 'Visualizador'
                ? module.id === 'anexos'
                : true
            )
            .map((module) => {
            const active =
              activeTab === module.id;

            const Icon = module.icon;

            return (
              <button
                key={module.id}
                type="button"
                className={`sidebar-module-button ${
                  active
                    ? 'sidebar-module-active'
                    : ''
                }`}
                onClick={() =>
                  onSelectTab(module.id)
                }
                title={
                  collapsed
                    ? module.label
                    : undefined
                }
              >
                <span className="sidebar-module-icon">
                  <Icon size={18} />
                </span>

                <span className="sidebar-module-content">
                  <span className="sidebar-module-label">
                    {module.label}
                  </span>

                  {active &&
                    activeCount !== undefined && (
                      <span className="sidebar-module-count">
                        {activeCount}
                      </span>
                    )}
                </span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          {collapsed ? (
            <span
              className="sidebar-footer-mini"
              title="Farmacias Dr. Simi"
            >
              TI
            </span>
          ) : (
            <>
              <strong>
                Farmacias Dr. Simi
              </strong>

              <span>
                Infraestructura TI
              </span>
            </>
          )}
        </div>
      </aside>
    </>
  );
}