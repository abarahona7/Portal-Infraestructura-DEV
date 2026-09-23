import {
  Edit,
  Trash2,
  History,
  Eye,
  MonitorCog
} from 'lucide-react';

import './PCsGenericosTable.css';

const MASKED_PASSWORD = '••••';

export default function PCsGenericosTable({
  pcs,
  onShowHistory,
  onEdit,
  onDelete,
  role,
  onRevealSecret,
}) {
  const togglePassword = (id) => { if (role === 'Administrador') onRevealSecret?.({ module: 'pc-generico', object_id: id, secret_type: 'password' }); };

  const PasswordField = ({ pc }) => {
    if (!pc.password_configured) {
      return (
        <span className="pc-password-empty">
          Sin contraseña
        </span>
      );
    }

    return (
      <div className="pc-password-container">
        <span className="pc-password-value">
          {MASKED_PASSWORD}
        </span>

        <button
          type="button"
          className="pc-password-button"
          onClick={() =>
            togglePassword(pc.id)
          }
          title="Mostrar contraseña"
          aria-label="Mostrar contraseña"
        >
          <Eye size={16} />
        </button>
      </div>
    );
  };

  const Actions = ({ pc }) => (
    <div className="pcs-actions">
      <button
        type="button"
        className="pc-action pc-action-history"
        onClick={() =>
          onShowHistory(pc)
        }
        title="Ver Historial"
        aria-label="Ver historial"
      >
        <History size={18} />
      </button>

      <button
        type="button"
        className="pc-action pc-action-edit"
        onClick={() =>
          onEdit(pc)
        }
        title="Editar"
        aria-label="Editar PC Genérico"
      >
        <Edit size={18} />
      </button>

      <button
        type="button"
        className="pc-action pc-action-delete"
        onClick={() =>
          onDelete(
            pc.id,
            pc.hostname
          )
        }
        title="Eliminar"
        aria-label="Eliminar PC Genérico"
      >
        <Trash2 size={18} />
      </button>
    </div>
  );

  return (
    <>
      {/* TABLA DESKTOP */}
      <div className="pcs-table-desktop">
        <table className="pcs-table">
          <thead>
            <tr>
              <th>Usuario Local</th>
              <th>Contraseña</th>
              <th>Hostname</th>
              <th>Departamento / Área</th>
              <th>Marca</th>
              <th>Modelo</th>
              <th>N.º de Serie</th>
              <th>Activo Fijo</th>
              <th>ID TeamViewer</th>
              <th>Observaciones</th>
              <th className="pcs-actions-header">
                Acciones
              </th>
            </tr>
          </thead>

          <tbody>
            {pcs.map((pc) => (
              <tr key={pc.id}>
                <td className="pc-user">
                  {pc.usuario_local || 'N/I'}
                </td>

                <td>
                  <PasswordField pc={pc} />
                </td>

                <td className="pc-hostname">
                  {pc.hostname || 'N/I'}
                </td>

                <td>
                  {pc.dpto_area || 'N/I'}
                </td>

                <td>
                  {pc.marca || 'N/I'}
                </td>

                <td>
                  {pc.modelo || 'N/I'}
                </td>

                <td className="pc-monospace">
                  {pc.numero_serie || 'N/I'}
                </td>

                <td className="pc-af">
                  {pc.activo_fijo || 'N/I'}
                </td>

                <td className="pc-monospace">
                  {pc.teamviewer_id || 'N/I'}
                </td>

                <td className="pc-observations">
                  {pc.observaciones ||
                    'Sin observaciones'}
                </td>

                <td className="pcs-actions-cell">
                  <Actions pc={pc} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* TARJETAS MÓVIL */}
      <div className="pcs-cards-mobile">
        {pcs.map((pc) => (
          <article
            key={pc.id}
            className="pc-card"
          >
            <div className="pc-card-header">
              <div className="pc-card-title">
                <span className="pc-card-icon">
                  <MonitorCog size={20} strokeWidth={2} />
                </span>

                <div>
                  <h3>
                    {pc.usuario_local ||
                      'Usuario local no informado'}
                  </h3>

                  <span className="pc-card-hostname">
                    Hostname · {pc.hostname || 'N/I'}
                  </span>
                </div>
              </div>
            </div>

            <div className="pc-card-password-section">
              <span className="pc-mobile-label">
                Contraseña
              </span>

              <PasswordField pc={pc} />
            </div>

            <div className="pc-card-grid">
              <MobileField
                label="Departamento / Área"
                value={
                  pc.dpto_area || 'N/I'
                }
                full
              />

              <MobileField
                label="Marca"
                value={pc.marca || 'N/I'}
              />

              <MobileField
                label="Modelo"
                value={pc.modelo || 'N/I'}
              />

              <MobileField
                label="N.º de Serie"
                value={
                  pc.numero_serie || 'N/I'
                }
                monospace
              />

              <MobileField
                label="Activo Fijo"
                value={
                  pc.activo_fijo || 'N/I'
                }
                monospace
              />

              <MobileField
                label="ID TeamViewer"
                value={
                  pc.teamviewer_id || 'N/I'
                }
                monospace
              />

              <MobileField
                label="Observaciones"
                value={
                  pc.observaciones ||
                  'Sin observaciones'
                }
                full
              />
            </div>

            <div className="pc-card-footer">
              <span className="pc-card-info">
                Gestión de PC Genérico
              </span>

              <Actions pc={pc} />
            </div>
          </article>
        ))}
      </div>

      {pcs.length === 0 && (
        <div className="pcs-empty">
          No existen PCs Genéricos para mostrar.
        </div>
      )}
    </>
  );
}

function MobileField({
  label,
  value,
  monospace = false,
  full = false,
}) {
  return (
    <div
      className={`pc-mobile-field ${full
        ? 'pc-mobile-field-full'
        : ''
        }`}
    >
      <span className="pc-mobile-label">
        {label}
      </span>

      <span
        className={`pc-mobile-value ${monospace
          ? 'pc-mobile-monospace'
          : ''
          }`}
      >
        {value}
      </span>
    </div>
  );
}
