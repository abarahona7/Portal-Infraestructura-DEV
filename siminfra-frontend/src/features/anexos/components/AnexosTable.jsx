import {
  Edit,
  History,
  PhoneCall
} from 'lucide-react';

import './AnexosTable.css';

export default function AnexosTable({
  anexos,
  renderAnexoStatusBadge,
  onShowHistory,
  onEdit,
  role,
}) {
  const isViewer = role === 'Visualizador';
  const canShowActions = !isViewer;

  const Actions = ({ anexo }) => canShowActions ? (
    <div className="anexos-actions">
      <button
        type="button"
        className="anexo-action anexo-action-history"
        onClick={() =>
          onShowHistory(anexo)
        }
        title="Ver historial"
        aria-label="Ver historial"
      >
        <History size={18} />
      </button>

      <button
        type="button"
        className="anexo-action anexo-action-edit"
        onClick={() => onEdit(anexo)}
        title="Editar"
        aria-label="Editar anexo"
      >
        <Edit size={18} />
      </button>
    </div>
  ) : null;

  return (
    <>
      {/* TABLA DESKTOP */}
      <div className="anexos-table-desktop">
        <table className="anexos-table">
          <thead>
            <tr>
              <th>Nombre Completo</th>
              <th>Departamento / Área</th>
              <th>Cargo</th>
              <th>Anexo</th>
              <th>Exterior</th>
              <th>Correo</th>
              <th>Estado</th>
              {!isViewer && <th>Observaciones</th>}

              {canShowActions && (
                <th className="anexos-actions-header">
                  Acciones
                </th>
              )}
            </tr>
          </thead>

          <tbody>
            {anexos.map((anexo) => (
              <tr key={anexo.id}>
                <td
                  className={
                    anexo.usuario_nombre
                      ? 'anexo-user-assigned'
                      : 'anexo-user-unassigned'
                  }
                >
                  {anexo.usuario_nombre ||
                    'Sin asignar'}
                </td>

                <td>
                  {anexo.departamento || '—'}
                </td>

                <td>
                  {anexo.cargo || '—'}
                </td>

                <td className="anexo-number">
                  {anexo.numero_anexo}
                </td>

                <td className="anexo-exterior">
                  {anexo.exterior || '—'}
                </td>

                <td>
                  {anexo.correo || '—'}
                </td>

                <td>
                  {renderAnexoStatusBadge(
                    anexo.estado
                  )}
                </td>

                {!isViewer && (
                  <td className="anexo-observations">
                    {anexo.observaciones ||
                      'Sin observaciones'}
                  </td>
                )}

                {canShowActions && (
                  <td className="anexos-actions-cell">
                    <Actions anexo={anexo} />
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* TARJETAS MÓVIL */}
      <div className="anexos-cards-mobile">
        {anexos.map((anexo) => (
          <article
            key={anexo.id}
            className="anexo-card"
          >
            <div className="anexo-card-header">
              <div className="anexo-card-title">
                <span className="anexo-card-icon">
                  <PhoneCall size={20} strokeWidth={2} />
                </span>

                <div>
                  <h3>
                    Anexo {anexo.numero_anexo}
                  </h3>

                  <span className="anexo-card-user">
                    {anexo.usuario_nombre ||
                      'Sin usuario asignado'}
                  </span>
                </div>
              </div>

              <div className="anexo-card-status">
                {renderAnexoStatusBadge(
                  anexo.estado
                )}
              </div>
            </div>

            <div className="anexo-card-grid">
              <MobileField
                label="Departamento / Área"
                value={
                  anexo.departamento || '—'
                }
              />

              <MobileField
                label="Cargo"
                value={
                  anexo.cargo || '—'
                }
              />

              <MobileField
                label="Exterior"
                value={
                  anexo.exterior || '—'
                }
                monospace
              />

              <MobileField
                label="Correo"
                value={
                  anexo.correo || '—'
                }
                full
              />

              {!isViewer && (
                <MobileField
                  label="Observaciones"
                  value={
                    anexo.observaciones ||
                    'Sin observaciones'
                  }
                  full
                />
              )}
            </div>

            {canShowActions && (
              <div className="anexo-card-footer">
                <span className="anexo-card-info">
                  Gestión de anexo
                </span>

                <Actions anexo={anexo} />
              </div>
            )}
          </article>
        ))}
      </div>

      {anexos.length === 0 && (
        <div className="anexos-empty">
          No existen anexos para mostrar.
        </div>
      )}
    </>
  );
}

function MobileField({
  label,
  value,
  full = false,
  monospace = false,
}) {
  return (
    <div
      className={`anexo-mobile-field ${full
          ? 'anexo-mobile-field-full'
          : ''
        }`}
    >
      <span className="anexo-mobile-label">
        {label}
      </span>

      <span
        className={`anexo-mobile-value ${monospace
            ? 'anexo-mobile-monospace'
            : ''
          }`}
      >
        {value}
      </span>
    </div>
  );
}
