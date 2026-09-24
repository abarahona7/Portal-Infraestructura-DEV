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
  usuarios = [],
  selectedDepartment,
  onSelectDepartment,
}) {
  const departmentMap = usuarios.reduce((acc, usuario) => {
    const department =
      usuario.departamento_nombre?.trim() ||
      usuario.dpto_area?.trim() ||
      'Sin Departamento';

    if (!acc[department]) {
      acc[department] = 0;
    }

    acc[department] += 1;
    return acc;
  }, {});

  const departments = Object.entries(departmentMap)
    .map(([value, count]) => ({
      value,
      label: getDepartmentLabel(value),
      count,
    }))
    .sort((a, b) =>
      a.label.localeCompare(b.label, 'es', { sensitivity: 'base' })
    );

  return (
    <section className="user-department-section">
      <div className="user-department-heading">
        <div>
          <h2>Departamentos / Áreas</h2>
          <p>Selecciona una categoría para visualizar sus usuarios.</p>
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
