import {
  Eye,
  EyeOff,
  Edit,
  Power,
  PowerOff,
  UserCog,
} from 'lucide-react';

import './PerfilesTable.css';

export default function PerfilesTable({
  perfiles,
  visiblePasswords,
  renderAccountTypeBadge,
  onEdit,
  onToggleStatus,
  role,
  onRevealSecret,
}) {
  const togglePassword = (id) => {
    if (role === 'Administrador') {
      onRevealSecret?.({
        module: 'perfil-generico',
        object_id: id,
        secret_type: 'password',
      });
    }
  };

  const PasswordField = ({ perfil }) => {
    const passwordVisible = Boolean(visiblePasswords?.[perfil.id]);

    if (!perfil.password_configured) {
      return <span className="perfil-no-password">Sin contraseña</span>;
    }

    return (
      <div className="perfil-password">
        <span className="perfil-password-value">••••••••</span>

        <button
          type="button"
          className="perfil-password-action"
          onClick={() => togglePassword(perfil.id)}
          title={passwordVisible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
          aria-label={passwordVisible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
        >
          {passwordVisible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
    );
  };

  const StatusBadge = ({ estado }) => {
    const active = estado !== 'INACTIVO';

    return (
      <span className={`perfil-status ${active ? 'is-active' : 'is-inactive'}`}>
        {active ? 'Activo' : 'Inactivo'}
      </span>
    );
  };

  const Actions = ({ perfil }) => {
    const active = perfil.estado !== 'INACTIVO';

    return (
      <div className="perfiles-actions">
        <button
          type="button"
          className="perfil-action perfil-action-edit"
          onClick={() => onEdit(perfil)}
          title="Editar perfil"
          aria-label={`Editar ${perfil.nombre || perfil.usuario || 'perfil'}`}
        >
          <Edit size={17} />
        </button>

        <button
          type="button"
          className={`perfil-action ${active ? 'perfil-action-deactivate' : 'perfil-action-activate'}`}
          onClick={() => onToggleStatus?.(perfil)}
          title={active ? 'Desactivar perfil' : 'Reactivar perfil'}
          aria-label={`${active ? 'Desactivar' : 'Reactivar'} ${perfil.nombre || perfil.usuario || 'perfil'}`}
        >
          {active ? <PowerOff size={17} /> : <Power size={17} />}
        </button>
      </div>
    );
  };

  if (!perfiles || perfiles.length === 0) {
    return (
      <div className="perfiles-empty">
        <UserCog size={28} aria-hidden="true" />
        <span>No existen perfiles para mostrar.</span>
      </div>
    );
  }

  return (
    <>
      <div className="perfiles-table-wrapper">
        <table className="perfiles-table">
          <thead>
            <tr>
              <th className="perfil-col-nombre">Nombre / Perfil</th>
              <th className="perfil-col-usuario">Usuario</th>
              <th className="perfil-col-password">Contraseña</th>
              <th className="perfil-col-tipo">Tipo Cuenta</th>
              <th className="perfil-col-correo">Correo Asignado</th>
              <th className="perfil-col-area">Departamento / Subárea</th>
              <th className="perfil-col-estado">Estado</th>
              <th className="perfil-col-observaciones">Observaciones</th>
              <th className="perfiles-actions-header">Acciones</th>
            </tr>
          </thead>

          <tbody>
            {perfiles.map((perfil) => (
              <tr
                key={perfil.id}
                className={perfil.estado === 'INACTIVO' ? 'perfil-row-inactive' : ''}
              >
                <td className="perfil-col-nombre perfil-nombre">
                  {perfil.nombre || 'N/I'}
                </td>

                <td className="perfil-col-usuario perfil-usuario">
                  {perfil.usuario || 'N/I'}
                </td>

                <td className="perfil-col-password">
                  <PasswordField perfil={perfil} />
                </td>

                <td className="perfil-col-tipo">
                  {renderAccountTypeBadge(perfil.tipo)}
                </td>

                <td className="perfil-col-correo perfil-correo">
                  {perfil.correo || 'N/I'}
                </td>

                <td className="perfil-col-area">
                  <div className="perfil-area-stack">
                    <strong>{perfil.departamento_nombre || 'Sin Departamento'}</strong>
                    <span>{perfil.subarea_nombre || 'Sin Subárea'}</span>
                  </div>
                </td>

                <td className="perfil-col-estado">
                  <StatusBadge estado={perfil.estado} />
                </td>

                <td className="perfil-col-observaciones">
                  {perfil.observaciones || 'Sin observaciones'}
                </td>

                <td className="perfiles-actions-cell">
                  <Actions perfil={perfil} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="perfiles-cards-mobile">
        {perfiles.map((perfil) => (
          <article
            key={perfil.id}
            className={`perfil-card ${perfil.estado === 'INACTIVO' ? 'is-inactive' : ''}`}
          >
            <div className="perfil-card-header">
              <div className="perfil-card-title">
                <span className="perfil-card-icon">
                  <UserCog size={21} strokeWidth={2} aria-hidden="true" />
                </span>

                <div className="perfil-card-heading-copy">
                  <h3>{perfil.nombre || 'Perfil genérico'}</h3>
                  <span>{perfil.usuario || 'Usuario no informado'}</span>
                </div>
              </div>

              <div className="perfil-card-type">
                {renderAccountTypeBadge(perfil.tipo)}
              </div>
            </div>

            <div className="perfil-card-password-section">
              <span className="perfil-mobile-label">Contraseña</span>
              <PasswordField perfil={perfil} />
            </div>

            <div className="perfil-card-grid">
              <MobileField
                label="Correo asignado"
                value={perfil.correo || 'N/I'}
                full
              />
              <MobileField
                label="Departamento"
                value={perfil.departamento_nombre || 'Sin Departamento'}
              />
              <MobileField
                label="Subárea"
                value={perfil.subarea_nombre || 'Sin Subárea'}
              />
              <MobileField
                label="Estado"
                value={<StatusBadge estado={perfil.estado} />}
              />
              <MobileField
                label="Observaciones"
                value={perfil.observaciones || 'Sin observaciones'}
                full
              />
            </div>

            <div className="perfil-card-footer">
              <span className="perfil-card-info">Gestión de perfil genérico</span>
              <Actions perfil={perfil} />
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

function MobileField({ label, value, full = false }) {
  return (
    <div className={`perfil-mobile-field ${full ? 'perfil-mobile-field-full' : ''}`}>
      <span className="perfil-mobile-label">{label}</span>
      <span className="perfil-mobile-value">{value}</span>
    </div>
  );
}
