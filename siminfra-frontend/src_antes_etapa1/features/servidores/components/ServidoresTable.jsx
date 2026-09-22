import {
  Edit,
  Trash2,
  Server
} from 'lucide-react';

import './ServidoresTable.css';

export default function ServidoresTable({
  servidores,
  onEdit,
  onDelete,
}) {
  const Actions = ({ servidor }) => (
    <div className="servidores-actions">
      <button
        type="button"
        className="servidor-action servidor-action-edit"
        onClick={() =>
          onEdit(servidor)
        }
        title="Editar"
        aria-label="Editar servidor"
      >
        <Edit size={18} />
      </button>

      <button
        type="button"
        className="servidor-action servidor-action-delete"
        onClick={() =>
          onDelete(
            servidor.id,
            servidor.hostname
          )
        }
        title="Eliminar"
        aria-label="Eliminar servidor"
      >
        <Trash2 size={18} />
      </button>
    </div>
  );

  return (
    <>
      {/* =========================
          TABLA DESKTOP
      ========================= */}

      <div className="servidores-table-desktop">
        <table className="servidores-table">
          <thead>
            <tr>
              <th>
                IP
              </th>

              <th>
                Hostname
              </th>

              <th>
                Descripción
              </th>

              <th className="servidores-actions-header">
                Acciones
              </th>
            </tr>
          </thead>

          <tbody>
            {servidores.map(
              (servidor) => (
                <tr key={servidor.id}>
                  {/* IP */}

                  <td className="servidor-ip">
                    {servidor.ip}
                  </td>

                  {/* HOSTNAME */}

                  <td className="servidor-hostname">
                    <div className="servidor-hostname-content">
                      <span className="servidor-icon-small">
                        <Server size={16} />
                      </span>

                      {servidor.hostname}
                    </div>
                  </td>

                  {/* DESCRIPCIÓN */}

                  <td className="servidor-description">
                    {servidor.descripcion ||
                      'Sin descripción'}
                  </td>

                  {/* ACCIONES */}

                  <td className="servidores-actions-cell">
                    <Actions
                      servidor={servidor}
                    />
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>


      {/* =========================
          TARJETAS RESPONSIVE
      ========================= */}

      <div className="servidores-cards-mobile">
        {servidores.map(
          (servidor) => (
            <article
              key={servidor.id}
              className="servidor-card"
            >
              {/* HEADER */}

              <div className="servidor-card-header">
                <div className="servidor-card-title">
                  <div className="servidor-card-icon">
                    <Server size={20} />
                  </div>

                  <div>
                    <h3>
                      {servidor.hostname}
                    </h3>

                    <span>
                      Servidor
                    </span>
                  </div>
                </div>
              </div>


              {/* DATOS */}

              <div className="servidor-card-grid">
                <MobileField
                  label="Dirección IP"
                  value={servidor.ip}
                  monospace
                />

                <MobileField
                  label="Descripción"
                  value={
                    servidor.descripcion ||
                    'Sin descripción'
                  }
                  full
                />
              </div>


              {/* FOOTER */}

              <div className="servidor-card-footer">
                <span className="servidor-card-info">
                  Gestión de servidor
                </span>

                <Actions
                  servidor={servidor}
                />
              </div>
            </article>
          )
        )}
      </div>


      {/* =========================
          SIN RESULTADOS
      ========================= */}

      {servidores.length === 0 && (
        <div className="servidores-empty">
          <Server size={28} />

          <span>
            No existen servidores para mostrar.
          </span>
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
      className={`servidor-mobile-field ${
        full
          ? 'servidor-mobile-field-full'
          : ''
      }`}
    >
      <span className="servidor-mobile-label">
        {label}
      </span>

      <span
        className={`servidor-mobile-value ${
          monospace
            ? 'servidor-mobile-monospace'
            : ''
        }`}
      >
        {value}
      </span>
    </div>
  );
}