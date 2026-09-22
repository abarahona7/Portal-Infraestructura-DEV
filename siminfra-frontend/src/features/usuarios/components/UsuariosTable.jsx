import {
  Edit,
  Trash2,
  History,
  UserRound,
} from 'lucide-react';

import './UsuariosTable.css';

export default function UsuariosTable({
  usuarios,
  onSelectUser,
  onShowHistory,
  onEdit,
  onDelete,
  renderStatusBadge,
}) {
  const getCelularCorporativo = (usuario) => {
    const celulares = (usuario.equipos || []).filter((equipo) => {
      const tipo = String(equipo.tipo || '')
        .trim()
        .toUpperCase();

      return tipo === 'CEL' || tipo === 'CELULAR';
    });

    const numeros = celulares
      .map((equipo) => equipo.numero_telefono)
      .filter(Boolean);

    const numerosUnicos = [...new Set(numeros)];

    return numerosUnicos.length === 0
      ? 'N/I'
      : numerosUnicos.join(' / ');
  };

  const Actions = ({ usuario }) => (
    <div className="usuarios-actions">
      <button
        type="button"
        className="usuario-action usuario-action-history"
        onClick={(e) => {
          e.stopPropagation();
          onShowHistory(usuario);
        }}
        title="Ver historial de modificaciones"
        aria-label={`Ver historial de ${usuario.nombre_completo || 'usuario'}`}
      >
        <History size={18} />
      </button>

      <button
        type="button"
        className="usuario-action usuario-action-edit"
        onClick={(e) => {
          e.stopPropagation();
          onEdit(usuario);
        }}
        title="Editar"
        aria-label={`Editar ${usuario.nombre_completo || 'usuario'}`}
      >
        <Edit size={18} />
      </button>

      <button
        type="button"
        className="usuario-action usuario-action-delete"
        onClick={(e) => {
          e.stopPropagation();
          onDelete(usuario.id, usuario.nombre_completo);
        }}
        title="Eliminar"
        aria-label={`Eliminar ${usuario.nombre_completo || 'usuario'}`}
      >
        <Trash2 size={18} />
      </button>
    </div>
  );

  if (usuarios.length === 0) {
    return (
      <div className="usuarios-empty">
        <UserRound size={28} aria-hidden="true" />
        <span>No existen usuarios para mostrar.</span>
      </div>
    );
  }

  return (
    <>
      <div className="usuarios-table-desktop">
        <table className="usuarios-table">
          <thead>
            <tr>
              <th>Nombre Completo</th>
              <th>Cargo</th>
              <th>Estado</th>
              <th>Usuario Red</th>
              <th>Hostname</th>
              <th>Correo Corp.</th>
              <th className="usuario-col-celular">Celular Corporativo</th>
              <th className="usuarios-actions-header">Acciones</th>
            </tr>
          </thead>

          <tbody>
            {usuarios.map((usuario) => (
              <tr
                key={usuario.id}
                onClick={() => onSelectUser(usuario)}
              >
                <td className="usuario-name">
                  {usuario.nombre_completo || 'N/I'}
                </td>

                <td className="usuario-secondary">
                  {usuario.cargo || 'N/I'}
                </td>

                <td>{renderStatusBadge(usuario.estado)}</td>

                <td className="usuario-red">
                  {usuario.usuario_red || 'N/I'}
                </td>

                <td className="usuario-hostname">
                  {usuario.hostname || 'N/I'}
                </td>

                <td className="usuario-correo">
                  {usuario.correo_corp || 'N/I'}
                </td>

                <td className="usuario-col-celular">
                  {getCelularCorporativo(usuario)}
                </td>

                <td className="usuarios-actions-cell">
                  <Actions usuario={usuario} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="usuarios-cards-mobile">
        {usuarios.map((usuario) => (
          <article
            key={usuario.id}
            className="usuario-card"
            onClick={() => onSelectUser(usuario)}
          >
            <div className="usuario-card-header">
              <div className="usuario-card-title">
                <span className="usuario-card-icon">
                  <UserRound size={21} strokeWidth={2} aria-hidden="true" />
                </span>

                <div className="usuario-card-heading-copy">
                  <h3>{usuario.nombre_completo || 'Usuario sin nombre'}</h3>
                  <span>{usuario.usuario_red || 'Sin usuario de red'}</span>
                </div>
              </div>

              <div className="usuario-card-status">
                {renderStatusBadge(usuario.estado)}
              </div>
            </div>

            <div className="usuario-card-grid">
              <MobileField
                label="Departamento"
                value={usuario.departamento_nombre || usuario.dpto_area || 'N/I'}
              />
              <MobileField
                label="Subárea"
                value={usuario.subarea_nombre || 'N/I'}
              />
              <MobileField
                label="Cargo"
                value={usuario.cargo || 'N/I'}
              />
              <MobileField
                label="Hostname"
                value={usuario.hostname || 'N/I'}
                monospace
              />
              <MobileField
                label="Celular corporativo"
                value={getCelularCorporativo(usuario)}
              />
              <MobileField
                label="Correo corporativo"
                value={usuario.correo_corp || 'N/I'}
                full
              />
            </div>

            <div className="usuario-card-footer">
              <span className="usuario-card-info">Gestión de usuario</span>
              <Actions usuario={usuario} />
            </div>
          </article>
        ))}
      </div>
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
      className={`usuario-mobile-field ${
        full ? 'usuario-mobile-field-full' : ''
      }`}
    >
      <span className="usuario-mobile-label">{label}</span>
      <span
        className={`usuario-mobile-value ${
          monospace ? 'usuario-mobile-monospace' : ''
        }`}
      >
        {value}
      </span>
    </div>
  );
}
