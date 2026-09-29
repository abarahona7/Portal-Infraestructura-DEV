import {
  Edit,
  Trash2,
  History,
  FileText,
  QrCode,
  Laptop,
  Monitor,
  Smartphone,
  Tablet,
  Printer,
  Wifi,
  Keyboard,
  Package,
  Eye,
} from 'lucide-react';

import {
  equipmentUsesHostname,
  equipmentUsesMobileLine,
  getEquipmentIdentifier,
  getEquipmentIdentifierLabel,
} from '../../../utils/equipmentHelpers';

import './EquiposTable.css';


const EquipmentIcon = ({ tipo }) => {
  const normalized = String(tipo || '')
    .trim()
    .toLowerCase();

  let Icon = Package;

  if (normalized.includes('notebook')) {
    Icon = Laptop;
  } else if (normalized === 'mac' || normalized.includes('macbook')) {
    Icon = Laptop;
  } else if (normalized.includes('monitor')) {
    Icon = Monitor;
  } else if (normalized.includes('celular') || normalized.includes('smartphone')) {
    Icon = Smartphone;
  } else if (normalized.includes('tablet')) {
    Icon = Tablet;
  } else if (normalized.includes('impresora')) {
    Icon = Printer;
  } else if (normalized.includes('router') || normalized.includes('bam')) {
    Icon = Wifi;
  } else if (
    normalized.includes('teclado') ||
    normalized.includes('mouse') ||
    normalized.includes('perif') ||
    normalized.includes('docking') ||
    normalized.includes('adaptador') ||
    normalized.includes('audífono') ||
    normalized.includes('audifono')
  ) {
    Icon = Keyboard;
  }

  return <Icon size={22} strokeWidth={2} aria-hidden="true" />;
};

export default function EquiposTable({
  equipos,
  formatEquipmentType,
  onShowHistory,
  onShowAssetMovements,
  onShowAssetQr,
  onEdit,
  onDelete,
  role,
  onRevealSecret,
}) {
  const showAssignedIp = equipos.length > 0 && equipos.every(
    (equipo) => formatEquipmentType(equipo.tipo) === 'Notebook'
  );

  /* =========================
     NORMALIZAR EQUIPO
  ========================= */

  const normalizeEquipo = (equipo) => ({
    ...equipo,
    tipo: formatEquipmentType(equipo.tipo),
  });


  /* =========================
     ACCIONES
  ========================= */

  const Actions = ({ equipo }) => (
    <div className="equipos-actions">
      <button type="button" className="equipo-action equipo-action-history" onClick={() => onShowAssetQr?.(equipo)} title="Abrir ficha y QR" aria-label="Abrir ficha y QR"><QrCode size={18} aria-hidden="true" /></button>
      <button type="button" className="equipo-action equipo-action-history" onClick={() => onShowAssetMovements?.(equipo)} title="Trazabilidad y actas" aria-label="Ver movimientos y actas"><FileText size={18} aria-hidden="true" /></button>
      <button
        type="button"
        className="equipo-action equipo-action-history"
        onClick={() => onShowHistory(equipo)}
        title="Ver Historial Auditoría"
        aria-label="Ver historial"
      >
        <History size={18} />
      </button>

      <button
        type="button"
        className="equipo-action equipo-action-edit"
        onClick={() => onEdit(equipo)}
        title="Editar"
        aria-label="Editar equipo"
      >
        <Edit size={18} />
      </button>

      <button
        type="button"
        className="equipo-action equipo-action-delete"
        onClick={() =>
          onDelete(
            equipo.id,
            `${equipo.marca || ''} ${equipo.modelo || ''
            }`
          )
        }
        title="Eliminar"
        aria-label="Eliminar equipo"
      >
        <Trash2 size={18} />
      </button>
    </div>
  );


  /* =========================
     NOMBRE COLUMNA IDENTIFICADOR
  ========================= */

  const getIdentifierColumnLabel = () => {
    if (!equipos || equipos.length === 0) {
      return 'Identificador';
    }

    const tipos = equipos.map(
      (equipo) =>
        formatEquipmentType(equipo.tipo)
          .trim()
          .toLowerCase()
    );

    const todosHostname = tipos.every(
      (tipo) =>
        ['notebook', 'mac'].includes(tipo)
    );

    if (todosHostname) {
      return 'Hostname';
    }

    const todosLineaMovil = tipos.every(
      (tipo) =>
        [
          'celular',
          'tablet',
          'bam / router',
        ].includes(tipo)
    );

    if (todosLineaMovil) {
      return 'SIM / N° Celular';
    }

    return 'Identificador';
  };


  /* =========================
     IDENTIFICADOR
  ========================= */

  const renderIdentifier = (equipo) => {
    const normalizedEquipo =
      normalizeEquipo(equipo);

    const identifier =
      getEquipmentIdentifier(
        normalizedEquipo
      );

    if (!identifier) {
      return (
        <span className="equipo-unassigned">
          N/A
        </span>
      );
    }

    if (
      equipmentUsesHostname(
        normalizedEquipo.tipo
      )
    ) {
      return (
        <span className="equipo-hostname">
          {identifier}
        </span>
      );
    }

    if (
      equipmentUsesMobileLine(
        normalizedEquipo.tipo
      )
    ) {
      return (
        <span className="equipo-mobile-line">
          {identifier}
        </span>
      );
    }

    return identifier;
  };

  /* =========================
   DETALLES SEGÚN TIPO
========================= */

  const renderEquipmentDetails = (equipo) => {
    const tipo = formatEquipmentType(equipo.tipo)
      .trim()
      .toLowerCase();

    const accesorios =
      equipo.accesorios?.trim() || '';

    // =========================
    // CELULAR
    // =========================

    if (tipo === 'celular') {
      return (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '2px',
            fontSize: '0.78rem'
          }}
        >
          <span>
            <strong>IMEI:</strong>{' '}
            {equipo.imei || 'N/I'}
          </span>

          <span>
            <strong>PIN:</strong>{' '}
            {renderPin(equipo)}
          </span>

          {accesorios && (
            <span>
              <strong>Accesorios:</strong>{' '}
              {accesorios}
            </span>
          )}
        </div>
      );
    }

    // =========================
    // RESTO DE EQUIPOS
    // =========================

    if (accesorios) {
      return (
        <div
          style={{
            fontSize: '0.78rem',
            lineHeight: '1.3'
          }}
        >
          <strong>Accesorios:</strong>{' '}
          {accesorios}
        </div>
      );
    }

    return (
      <span className="equipo-unassigned">
        N/A
      </span>
    );
  };

  const renderPin = (equipo) => {
    if (!equipo.pin_configured) {
      return 'N/I';
    }

    return (
      <span className="equipo-secret-value">
        <span aria-label="PIN configurado">••••</span>
        {role === 'Administrador' && (
          <button
            type="button"
            className="equipo-secret-reveal"
            onClick={() => onRevealSecret?.({
              module: 'equipamiento',
              object_id: equipo.id,
              secret_type: 'pin',
            })}
            aria-label={`Revelar PIN de ${equipo.marca || ''} ${equipo.modelo || ''}`.trim()}
            title="Revelar PIN"
          >
            <Eye size={16} aria-hidden="true" />
          </button>
        )}
      </span>
    );
  };

  return (
    <>
      {/* =========================
          TABLA DESKTOP
      ========================= */}

      <div className="equipos-table-desktop">
        <table className="equipos-table">
          <thead>
            <tr>
              <th>
                Tipo
              </th>

              <th>
                Marca / Modelo
              </th>

              <th>
                N° Serie
              </th>

              <th>
                Activo Fijo (AF)
              </th>

              <th>
                {getIdentifierColumnLabel()}
              </th>

              {showAssignedIp && (
                <th>IP asignada</th>
              )}

              <th>
                Detalles
              </th>

              <th>
                Asignado a
              </th>

              <th>
                Fecha Asignación
              </th>

              <th>
                Estado
              </th>

              <th className="equipos-actions-header">
                Acciones
              </th>
            </tr>
          </thead>

          <tbody>
            {equipos.map((equipo) => (
              <tr key={equipo.id}>

                {/* TIPO */}

                <td className="equipo-type">
                  {formatEquipmentType(
                    equipo.tipo
                  )}
                </td>


                {/* MARCA / MODELO */}

                <td>
                  {`${equipo.marca || ''} ${equipo.modelo || ''
                    }`.trim() || 'N/I'}
                </td>


                {/* SERIE */}

                <td className="equipo-monospace">
                  {equipo.numero_serie ||
                    'N/I'}
                </td>


                {/* AF */}

                <td className="equipo-af">
                  {equipo.af || 'N/I'}
                </td>


                {/* IDENTIFICADOR */}

                <td className="equipo-identifier">
                  {renderIdentifier(equipo)}
                </td>

                {showAssignedIp && (
                  <td className="equipo-monospace">
                    {equipo.ip_asignada || 'N/A'}
                  </td>
                )}


                {/* DETALLES */}

                <td>
                  {renderEquipmentDetails(equipo)}
                </td>


                {/* ASIGNADO A */}

                <td
                  className={
                    equipo.usuario_nombre
                      ? 'equipo-assigned'
                      : 'equipo-unassigned'
                  }
                >
                  {equipo.usuario_nombre ||
                    'Disponible (Stock)'}
                </td>


                {/* FECHA */}

                <td className="equipo-date">
                  {equipo.fecha_asignacion ||
                    'N/A'}
                </td>


                {/* ESTADO */}

                <td>
                  {equipo.estado ||
                    'ASIGNADO'}
                </td>


                {/* ACCIONES */}

                <td className="equipos-actions-cell">
                  <Actions equipo={equipo} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>


      {/* =========================
          TARJETAS RESPONSIVE
      ========================= */}

      <div className="equipos-cards-mobile">
        {equipos.map((equipo) => {
          const normalizedEquipo =
            normalizeEquipo(equipo);

          const identifier =
            getEquipmentIdentifier(
              normalizedEquipo
            );

          const identifierLabel =
            getEquipmentIdentifierLabel(
              normalizedEquipo.tipo
            );

          return (
            <article
              key={equipo.id}
              className="equipo-card"
            >
              {/* HEADER */}

              <div className="equipo-card-header">
                <div className="equipo-card-title">
                  <span className="equipo-card-icon">
                  <EquipmentIcon tipo={equipo.tipo} />
                  </span>

                  <div>
                    <h3>
                      {`${equipo.marca || ''} ${equipo.modelo || ''
                        }`.trim() ||
                        'Equipo sin marca/modelo'}
                    </h3>

                    <span className="equipo-card-type">
                      {formatEquipmentType(
                        equipo.tipo
                      )}
                    </span>
                  </div>
                </div>

                <span
                  className={`equipo-card-status ${equipo.usuario_nombre
                    ? 'equipo-card-status-assigned'
                    : 'equipo-card-status-stock'
                    }`}
                >
                  {equipo.estado ||
                    (equipo.usuario_nombre
                      ? 'ASIGNADO'
                      : 'STOCK')}
                </span>
              </div>


              {/* DATOS */}

              <div className="equipo-card-grid">

                <MobileField
                  label="N° Serie"
                  value={
                    equipo.numero_serie ||
                    'N/I'
                  }
                  monospace
                />

                <MobileField
                  label="Activo Fijo"
                  value={
                    equipo.af ||
                    'N/I'
                  }
                  monospace
                />

                {identifierLabel && (
                  <MobileField
                    label={identifierLabel}
                    value={
                      identifier ||
                      'N/A'
                    }
                    monospace
                  />
                )}

                {showAssignedIp && (
                  <MobileField
                    label="IP asignada"
                    value={equipo.ip_asignada || 'N/A'}
                    monospace
                  />
                )}

                {equipo.accesorios?.trim() && (
                  <MobileField
                    label="Accesorios"
                    value={equipo.accesorios}
                    full
                  />
                )}

                {formatEquipmentType(equipo.tipo) === 'Celular' && (
                  <>
                    <MobileField
                      label="IMEI"
                      value={equipo.imei || 'N/I'}
                      monospace
                    />

                    <MobileField
                      label="PIN"
                      value={renderPin(equipo)}
                      monospace
                    />
                  </>
                )}

                <MobileField
                  label="Asignado a"
                  value={
                    equipo.usuario_nombre ||
                    'Disponible (Stock)'
                  }
                  full
                />

                <MobileField
                  label="Fecha Asignación"
                  value={
                    equipo.fecha_asignacion ||
                    'N/A'
                  }
                />

                <MobileField
                  label="Estado"
                  value={
                    equipo.estado ||
                    'ASIGNADO'
                  }
                />
              </div>


              {/* FOOTER */}

              <div className="equipo-card-footer">
                <span className="equipo-card-info">
                  Gestión de equipo
                </span>

                <Actions equipo={equipo} />
              </div>
            </article>
          );
        })}
      </div>


      {/* =========================
          VACÍO
      ========================= */}

      {equipos.length === 0 && (
        <div className="equipos-empty">
          No existen equipos para mostrar.
        </div>
      )}
    </>
  );
}


/* =========================
   CAMPO TARJETA
========================= */

function MobileField({
  label,
  value,
  monospace = false,
  full = false,
}) {
  return (
    <div
      className={`equipo-mobile-field ${full
        ? 'equipo-mobile-field-full'
        : ''
        }`}
    >
      <span className="equipo-mobile-label">
        {label}
      </span>

      <span
        className={`equipo-mobile-value ${monospace
          ? 'equipo-mobile-monospace'
          : ''
          }`}
      >
        {value}
      </span>
    </div>
  );
}
