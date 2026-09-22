import './PerfilDepartmentCards.css';

const getCount = (profiles, predicate) =>
  profiles.reduce((count, profile) => (predicate(profile) ? count + 1 : count), 0);

export default function PerfilDepartmentCards({
  perfiles = [],
  departamentos = [],
  selectedFilter = '',
  onSelectFilter,
}) {
  const selectedDepartmentId = selectedFilter.startsWith('dept:')
    ? Number(selectedFilter.split(':')[1])
    : selectedFilter.startsWith('subarea:')
      ? departamentos.find((department) =>
          (department.subareas || []).some(
            (subarea) => Number(subarea.id) === Number(selectedFilter.split(':')[1])
          )
        )?.id
      : null;

  const selectedDepartment = departamentos.find(
    (department) => Number(department.id) === Number(selectedDepartmentId)
  );

  const visibleDepartments = departamentos
    .map((department) => ({
      ...department,
      count: getCount(
        perfiles,
        (perfil) => Number(perfil.departamento) === Number(department.id)
      ),
    }))
    .filter((department) => department.count > 0 || department.activo)
    .sort((a, b) =>
      (a.nombre || '').localeCompare(b.nombre || '', 'es', { sensitivity: 'base' })
    );

  const subareas = (selectedDepartment?.subareas || [])
    .map((subarea) => ({
      ...subarea,
      count: getCount(
        perfiles,
        (perfil) => Number(perfil.subarea) === Number(subarea.id)
      ),
    }))
    .filter((subarea) => subarea.count > 0 || subarea.activo)
    .sort((a, b) =>
      (a.nombre || '').localeCompare(b.nombre || '', 'es', { sensitivity: 'base' })
    );

  return (
    <section className="perfil-department-section">
      <div className="perfil-department-heading">
        <div>
          <h2>Perfiles por Departamento / Subárea</h2>
          <p>Selecciona un Departamento y, si corresponde, una Subárea.</p>
        </div>

        {selectedFilter && (
          <button
            type="button"
            className="perfil-department-clear"
            onClick={() => onSelectFilter('')}
          >
            Ver todos
          </button>
        )}
      </div>

      <div className="perfil-department-grid">
        {visibleDepartments.map((department) => {
          const value = `dept:${department.id}`;
          const active = Number(selectedDepartmentId) === Number(department.id);

          return (
            <button
              key={department.id}
              type="button"
              className={`perfil-department-card ${active ? 'is-active' : ''}`}
              onClick={() => onSelectFilter(active && selectedFilter === value ? '' : value)}
            >
              <span className="perfil-department-name">{department.nombre}</span>
              <span className="perfil-department-count">{department.count}</span>
            </button>
          );
        })}
      </div>

      {selectedDepartment && subareas.length > 0 && (
        <div className="perfil-subarea-block">
          <span className="perfil-subarea-label">Subáreas de {selectedDepartment.nombre}</span>

          <div className="perfil-subarea-grid">
            {subareas.map((subarea) => {
              const value = `subarea:${subarea.id}`;
              const active = selectedFilter === value;

              return (
                <button
                  key={subarea.id}
                  type="button"
                  className={`perfil-subarea-chip ${active ? 'is-active' : ''}`}
                  onClick={() => onSelectFilter(active ? `dept:${selectedDepartment.id}` : value)}
                >
                  <span>{subarea.nombre}</span>
                  <strong>{subarea.count}</strong>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
