import {
  Building2,
  Users,
} from 'lucide-react';

import './UserDepartmentCards.css';

const getDepartmentLabel = (department) => {
  if (!department) {
    return 'Sin Departamento';
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

export default function UserDepartmentCards({
  usuarios = [],
  selectedDepartment,
  onSelectDepartment,
}) {
  const departmentMap = usuarios.reduce(
    (acc, usuario) => {
      const department =
        usuario.dpto_area?.trim() ||
        'Sin Departamento';

      if (!acc[department]) {
        acc[department] = 0;
      }

      acc[department] += 1;

      return acc;
    },
    {}
  );

  const departments = Object.entries(
    departmentMap
  )
    .map(([value, count]) => ({
      value,
      label: getDepartmentLabel(value),
      count,
    }))
    .sort((a, b) =>
      a.label.localeCompare(
        b.label,
        'es',
        { sensitivity: 'base' }
      )
    );

  return (
    <section className="user-department-section">
      <div className="user-department-heading">
        <div>
          <h2>
            Selecciona un Departamento / Área
          </h2>

          <p>
            Visualiza los colaboradores según el
            área a la que pertenecen.
          </p>
        </div>

        {selectedDepartment && (
          <button
            type="button"
            className="user-department-clear"
            onClick={() =>
              onSelectDepartment('')
            }
          >
            Limpiar selección
          </button>
        )}
      </div>

      <div className="user-department-grid">
        {departments.map((department) => {
          const active =
            selectedDepartment ===
            department.value;

          return (
            <button
              key={department.value}
              type="button"
              className={`user-department-card ${
                active ? 'is-active' : ''
              }`}
              onClick={() =>
                onSelectDepartment(
                  department.value
                )
              }
            >
              <div className="user-department-icon">
                {department.value ===
                'Sin Departamento' ? (
                  <Users size={20} />
                ) : (
                  <Building2 size={20} />
                )}
              </div>

              <div className="user-department-content">
                <span className="user-department-name">
                  {department.label}
                </span>

                <div className="user-department-count">
                  <strong>
                    {department.count}
                  </strong>

                  <span>
                    {department.count === 1
                      ? ' usuario'
                      : ' usuarios'}
                  </span>
                </div>

                <span className="user-department-action">
                  Ver usuarios →
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}