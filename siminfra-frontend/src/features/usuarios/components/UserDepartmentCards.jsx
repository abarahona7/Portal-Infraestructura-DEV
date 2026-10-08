import './UserDepartmentCards.css';

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
          <p>Selecciona un departamento para filtrar la lista de usuarios.</p>
        </div>

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
