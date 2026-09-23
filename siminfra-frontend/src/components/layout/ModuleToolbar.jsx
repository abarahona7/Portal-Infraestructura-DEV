import './ModuleToolbar.css';

import {
  Download,
  Filter,
  Plus
} from 'lucide-react';

export default function ModuleToolbar({
  activeTab,
  departments,
  selectedDepartment,
  onDepartmentChange,
  selectedEquipmentStatus,
  onEquipmentStatusChange,
  selectedIpStatus,
  onIpStatusChange,
  selectedAnexoStatus,
  onAnexoStatusChange,
  search,
  onSearchChange,
  onCreate,
  onExport,
  readOnly = false,
}) {
  const getCreateLabel = () => {
    switch (activeTab) {
      case 'usuarios':
        return 'Usuario';

      case 'equipos':
        return 'Equipo';

      case 'pcs-genericos':
        return 'PC Genérico';

      case 'servidores':
        return 'Servidor';

      case 'perfiles':
        return 'Perfil';

      case 'ips':
        return 'IP';

      case 'anexos':
        return 'Anexo';

      default:
        return 'Registro';
    }
  };

  const getSearchPlaceholder = () => {
    switch (activeTab) {
      case 'usuarios':
        return 'Buscar por nombre, usuario, correo, hostname...';

      case 'equipos':
        return 'Buscar por marca, modelo, serie, hostname, AF...';

      case 'pcs-genericos':
        return 'Buscar por usuario, hostname, marca, modelo...';

      case 'servidores':
        return 'Buscar por IP, hostname o descripción...';

      case 'perfiles':
        return 'Buscar por nombre, usuario o correo...';

      case 'ips':
        return 'Buscar por IP, usuario u observación...';

      case 'anexos':
        return 'Buscar por anexo, usuario, departamento, cargo...';

      default:
        return 'Buscar...';
    }
  };

  return (
    <div className="module-toolbar">
      <div className="module-toolbar-actions">

        {/* BOTÓN AGREGAR */}
        {!readOnly && (
        <button
          type="button"
          onClick={onCreate}
          className="module-toolbar-create"
        >
          <Plus size={18} />

          <span>
            Agregar {getCreateLabel()}
          </span>
        </button>
        )}

        {/* BOTÓN EXPORTAR EXCEL */}
        {!readOnly && onExport && (
          <button
            type="button"
            onClick={onExport}
            className="module-toolbar-export"
          >
            <Download size={18} />

            <span>
              Exportar Excel
            </span>
          </button>
        )}


        {/* FILTRO DEPARTAMENTO */}
        {(
          activeTab === 'pcs-genericos'
        ) && (
          <div className="module-toolbar-filter">
            <Filter size={16} />

            <select
              value={selectedDepartment}
              onChange={(e) =>
                onDepartmentChange(
                  e.target.value
                )
              }
            >
              <option value="">
                Todos los Departamentos
              </option>

              {departments.map(
                (department, index) => (
                  <option
                    key={index}
                    value={department}
                  >
                    {department}
                  </option>
                )
              )}
            </select>
          </div>
        )}


        {/* FILTRO EQUIPOS */}
        {activeTab === 'equipos' && (
          <div className="module-toolbar-filter">
            <Filter size={16} />

            <select
              value={selectedEquipmentStatus}
              onChange={(event) =>
                onEquipmentStatusChange(event.target.value)
              }
            >
              <option value="">Todos los Estados</option>
              <option value="ASIGNADO">Asignado</option>
              <option value="STOCK">Stock / Disponible</option>
              <option value="MANTENCION">En Mantención</option>
              <option value="BAJA">Dado de Baja</option>
            </select>
          </div>
        )}


        {/* FILTRO IP */}
        {activeTab === 'ips' && (
          <div className="module-toolbar-filter">
            <Filter size={16} />

            <select
              value={selectedIpStatus}
              onChange={(e) =>
                onIpStatusChange(
                  e.target.value
                )
              }
            >
              <option value="">
                Todos los Estados
              </option>

              <option value="LIBRE">
                Libre
              </option>

              <option value="RESERVADA">
                Reservada
              </option>

            </select>
          </div>
        )}


        {/* FILTRO ANEXOS */}
        {activeTab === 'anexos' && (
          <div className="module-toolbar-filter">
            <Filter size={16} />

            <select
              value={selectedAnexoStatus}
              onChange={(e) =>
                onAnexoStatusChange(
                  e.target.value
                )
              }
            >
              <option value="">
                Todos los Estados
              </option>

              <option value="DISPONIBLE">
                Disponible
              </option>

              <option value="ASIGNADO">
                Asignado
              </option>
            </select>
          </div>
        )}


        {/* BUSCADOR */}
        <div className="module-toolbar-search">
          <input
            type="text"
            placeholder={
              getSearchPlaceholder()
            }
            value={search}
            onChange={(e) =>
              onSearchChange(
                e.target.value
              )
            }
          />
        </div>
      </div>
    </div>
  );
}
