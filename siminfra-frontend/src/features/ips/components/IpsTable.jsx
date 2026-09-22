import {
  Edit,
  Trash2,
  Network
} from 'lucide-react';

import './IpsTable.css';

export default function IpsTable({
  ips,
  renderIpStatusBadge,
  onEdit,
  onDelete,
}) {
  const Actions = ({ ip }) => {
    const deleteBlocked = Boolean(ip.usuario);

    return (
      <div className="ips-actions">
        <button
          type="button"
          className="ip-action ip-action-edit"
          onClick={() => onEdit(ip)}
          title="Editar"
          aria-label="Editar IP"
        >
          <Edit size={18} />
        </button>

        <button
          type="button"
          className="ip-action ip-action-delete"
          onClick={() => {
            if (!deleteBlocked) {
              onDelete(ip.id, ip.direccion_ip);
            }
          }}
          disabled={deleteBlocked}
          title={
            deleteBlocked
              ? 'Libera esta IP desde la ficha del usuario antes de eliminarla'
              : 'Eliminar'
          }
          aria-label={
            deleteBlocked
              ? 'IP asignada a usuario; no se puede eliminar'
              : 'Eliminar IP'
          }
          style={
            deleteBlocked
              ? { opacity: 0.4, cursor: 'not-allowed' }
              : undefined
          }
        >
          <Trash2 size={18} />
        </button>
      </div>
    );
  };

  return (
    <>
      {/* TABLA DESKTOP */}
      <div className="ips-table-desktop">
        <table className="ips-table">
          <thead>
            <tr>
              <th>Dirección IP</th>
              <th>Estado</th>
              <th>Asignado a</th>
              <th>Observaciones</th>

              <th className="ips-actions-header">
                Acciones
              </th>
            </tr>
          </thead>

          <tbody>
            {ips.map((ip) => (
              <tr key={ip.id}>
                <td className="ip-address">
                  {ip.direccion_ip}
                </td>

                <td>
                  {renderIpStatusBadge(
                    ip.estado
                  )}
                </td>

                <td
                  className={
                    ip.usuario_nombre ||
                      ip.asignado_otro
                      ? 'ip-assigned'
                      : 'ip-unassigned'
                  }
                >
                  {ip.usuario_nombre ||
                    ip.asignado_otro ||
                    'Sin asignar'}
                </td>

                <td className="ip-observation">
                  {ip.observacion ||
                    'Sin observaciones'}
                </td>

                <td className="ips-actions-cell">
                  <Actions ip={ip} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* TARJETAS MÓVIL */}
      <div className="ips-cards-mobile">
        {ips.map((ip) => (
          <article
            key={ip.id}
            className="ip-card"
          >
            <div className="ip-card-header">
              <div className="ip-card-title">
                <span className="ip-card-icon">
                  <Network size={20} strokeWidth={2} />
                </span>

                <div>
                  <h3>
                    {ip.direccion_ip}
                  </h3>

                  <span className="ip-card-subtitle">
                    Dirección IP
                  </span>
                </div>
              </div>

              <div className="ip-card-status">
                {renderIpStatusBadge(
                  ip.estado
                )}
              </div>
            </div>

            <div className="ip-card-grid">
              <MobileField
                label="Asignado a"
                value={
                  ip.usuario_nombre ||
                  ip.asignado_otro ||
                  'Sin asignar'
                }
                full
              />

              <MobileField
                label="Observaciones"
                value={
                  ip.observacion ||
                  'Sin observaciones'
                }
                full
              />
            </div>

            <div className="ip-card-footer">
              <span className="ip-card-info">
                Gestión de IP
              </span>

              <Actions ip={ip} />
            </div>
          </article>
        ))}
      </div>

      {ips.length === 0 && (
        <div className="ips-empty">
          No existen direcciones IP para mostrar.
        </div>
      )}
    </>
  );
}

function MobileField({
  label,
  value,
  full = false,
}) {
  return (
    <div
      className={`ip-mobile-field ${full
          ? 'ip-mobile-field-full'
          : ''
        }`}
    >
      <span className="ip-mobile-label">
        {label}
      </span>

      <span className="ip-mobile-value">
        {value}
      </span>
    </div>
  );
}