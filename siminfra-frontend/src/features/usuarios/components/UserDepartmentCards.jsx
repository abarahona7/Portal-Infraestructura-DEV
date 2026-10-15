import './UserDepartmentCards.css';
import { UserX } from 'lucide-react';

const getDepartmentLabel = (department) => {
  if (!department) {
    return 'Sin Departamento';
  }

  const normalizedDepartment = department.trim().toLowerCase();

  if (
    normalizedDepartment === 'infraestructura ti' ||
    normalizedDepartment === 'ti'
  ) {
    return 'TECNOLOGÍA';
  }

  return department;
};

export default function UserDepartmentCards({
  stats = { departamentos: [] },
  selectedDepartment,
  onSelectDepartment,
  selectedStatus,
  onSelectStatus,
}) {
  const departments = (stats.departamentos || [])
    .map((department) => ({
      value: department.nombre,
      label: getDepartmentLabel(department.nombre),
      count: department.total,
    }))
    .sort((a, b) =>
      a.label.localeCompare(b.label, 'es', { sensitivity: 'base' })
    );

  return (
    <section className="user-department-section">
      <div className="user-department-heading">
        <div>
          <h2>Departamentos / Áreas</h2>
          <p>Usuarios activos o con licencia médica, agrupados por departamento.</p>
        </div>

        <div className="user-department-heading-actions">
          <button
            type="button"
            aria-pressed={selectedStatus === 'BAJA'}
            className={`user-inactive-button ${selectedStatus === 'BAJA' ? 'is-active' : ''}`}
            onClick={() => onSelectStatus(selectedStatus === 'BAJA' ? '' : 'BAJA')}
          >
            <UserX size={17} aria-hidden="true" />
            <span>Usuarios de baja</span>
            <strong>{stats.baja || 0}</strong>
          </button>

          {selectedDepartment && (
            <button
              type="button"
              className="user-department-clear"
              onClick={() => onSelectDepartment('')}
            >
              Ver todos
            </button>
          )}
        </div>
      </div>

      <div className="user-department-grid">
        {departments.map((department) => {
          const active = selectedDepartment === department.value;

          return (
            <button
              key={department.value}
              type="button"
              aria-pressed={active}
              className={`user-department-card ${active ? 'is-active' : ''}`}
              onClick={() => onSelectDepartment(department.value)}
            >
              <span className="user-department-name">{department.label}</span>
              <span className="user-department-count">{department.count}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
