import { useState } from 'react';

import {
  X,
  Eye,
  UserRound,
  AtSign,
  Monitor,
  Network,
  Mail,
  Smartphone,
  Phone,
  Building2,
  KeyRound,
  ShieldCheck,
  Laptop,
  Tablet,
  Router,
  HardDrive,
  Package,
  Cloud,
  Hash,
  Cpu,
  FileText,
} from 'lucide-react';

import {
  getActaEntregaUsuario,
} from '../../../api/usuariosApi';

import {
  equipmentUsesHostname,
  getEquipmentIdentifier,
  getEquipmentIdentifierLabel,
} from '../../../utils/equipmentHelpers';

import './UsuarioDetailModal.css';


export default function UsuarioDetailModal({
  usuario,
  onClose,
  renderStatusBadge,
  formatEquipmentType,
  role,
  onRevealSecret,
}) {
  const [generatingActa, setGeneratingActa] =
    useState(false);

  if (!usuario) {
    return null;
  }

  const hasAssignedEquipment = Boolean(usuario.equipos?.length);
  const actaUnavailableMessage = (
    'No se puede generar el Acta de Entrega porque este usuario no tiene equipos o insumos asignados.'
  );

  const handleGenerateActa = async () => {
    if (!usuario?.id || generatingActa) {
      return;
    }

    if (!hasAssignedEquipment) {
      return;
    }

    const pdfWindow = window.open(
      '',
      '_blank'
    );

    try {
      setGeneratingActa(true);

      const pdfBlob =
        await getActaEntregaUsuario(
          usuario.id
        );

      const pdfUrl =
        URL.createObjectURL(
          new Blob(
            [pdfBlob],
            {
              type: 'application/pdf',
            }
          )
        );

      if (pdfWindow) {
        pdfWindow.location.href = pdfUrl;
      } else {
        window.open(
          pdfUrl,
          '_blank',
          'noopener,noreferrer'
        );
      }

      /*
        Dejamos un tiempo antes de liberar
        la URL para que el navegador cargue
        correctamente el PDF.
      */
      setTimeout(() => {
        URL.revokeObjectURL(pdfUrl);
      }, 60000);

    } catch (error) {
      console.error(
        'Error generando acta:',
        error
      );

      if (pdfWindow) {
        pdfWindow.close();
      }

      alert(
        error.response?.data?.detail
        || 'No se pudo generar el Acta de Entrega.'
      );

    } finally {
      setGeneratingActa(false);
    }
  };


  /* =========================
     CELULAR CORPORATIVO
  ========================= */

  const celularesAsignados =
    (usuario.equipos || []).filter(
      (equipo) =>
        formatEquipmentType(
          equipo.tipo
        ) === 'Celular'
    );

  const numerosCelular =
    celularesAsignados
      .map(
        (equipo) =>
          equipo.numero_telefono
      )
      .filter(Boolean);

  const celularCorporativo =
    numerosCelular.length > 0
      ? numerosCelular.join(' / ')
      : null;


  /* =========================
     ICONO EQUIPO
  ========================= */

  const getEquipmentIcon = (
    tipo
  ) => {
    switch (tipo) {
      case 'Notebook':
        return Laptop;

      case 'Mac':
        return Monitor;

      case 'Celular':
        return Smartphone;

      case 'Tablet':
        return Tablet;

      case 'BAM / Router':
        return Router;

      case 'Monitor':
        return Monitor;

      case 'Docking':
        return HardDrive;

      default:
        return Package;
    }
  };


  return (
    <div
      className="user-detail-overlay"
      role="presentation"
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          onClose?.();
        }
      }}
    >
      <section
        className="user-detail-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="user-detail-title"
      >

        {/* HEADER */}

        <div className="user-detail-header">
          <div className="user-detail-header-user">

            <div className="user-detail-avatar">
              <UserRound size={26} />
            </div>

            <div className="user-detail-header-info">

              <div className="user-detail-header-top">
                <h2 id="user-detail-title">
                  {usuario.nombre_completo ||
                    'Usuario'}
                </h2>

                {renderStatusBadge(
                  usuario.estado
                )}
              </div>

              <div className="user-detail-subtitle">
                <span>
                  {usuario.cargo ||
                    'Sin cargo'}
                </span>

                <span className="user-detail-separator">
                  •
                </span>

                <span>
                  {usuario.departamento_nombre ||
                    usuario.dpto_area ||
                    'Sin departamento'}
                  {usuario.subarea_nombre
                    ? ` / ${usuario.subarea_nombre}`
                    : ''}
                </span>
              </div>

            </div>
          </div>

          <div className="user-detail-header-actions">

            <button
              type="button"
              className={`user-detail-acta-button ${generatingActa ? 'is-generating' : ''}`}
              onClick={handleGenerateActa}
              disabled={generatingActa || !hasAssignedEquipment}
              title={
                hasAssignedEquipment
                  ? 'Crear Acta de Entrega'
                  : actaUnavailableMessage
              }
              aria-label="Crear Acta de Entrega"
              aria-describedby={
                hasAssignedEquipment
                  ? undefined
                  : 'acta-unavailable-reason'
              }
            >
              <FileText size={17} />

              <span>
                {generatingActa
                  ? 'Generando...'
                  : 'Crear Acta de Entrega'}
              </span>
            </button>

            <button
              type="button"
              className="user-detail-close"
              onClick={onClose}
              title="Cerrar"
              aria-label="Cerrar ficha de usuario"
            >
              <X size={21} />
            </button>

          </div>
        </div>


        {/* CONTENT */}

        <div className="user-detail-content">

          {/* INFORMACIÓN GENERAL */}

          <SectionHeader
            title="Información General"
            subtitle="Datos corporativos y de conectividad"
          />

          <div className="user-detail-info-grid">

            <InfoCard
              icon={AtSign}
              label="Usuario de Red"
              value={
                usuario.usuario_red ||
                'N/I'
              }
            />

            <InfoCard
              icon={Monitor}
              label="Hostname"
              value={
                usuario.hostname ||
                'Sin hostname'
              }
              accent
            />

            <InfoCard
              icon={Network}
              label="IP Asignada"
              value={
                usuario.ip_actual ||
                'Sin IP asignada'
              }
              accent={Boolean(
                usuario.ip_actual
              )}
            />

            <InfoCard
              icon={Mail}
              label="Correo Corporativo"
              value={
                usuario.correo_corp ||
                'Sin correo'
              }
              compact
            />
            <InfoCard
              icon={Smartphone}
              label="Celular Corporativo"
              value={
                celularCorporativo ||
                'Sin celular asignado'
              }
              accent={Boolean(
                celularCorporativo
              )}
            />

            <InfoCard
              icon={Phone}
              label="Anexo"
              value={
                usuario.anexo_actual
                  ?.numero_anexo ||
                'Sin anexo asignado'
              }
              accent={Boolean(
                usuario.anexo_actual
              )}
            />

            <InfoCard
              icon={Building2}
              label="Exterior"
              value={
                usuario.anexo_actual
                  ?.exterior ||
                'Sin exterior'
              }
            />

          </div>


          {/* CREDENCIALES */}

          <section className="user-detail-section">

            <SectionHeader
              title="Credenciales"
              subtitle="Accesos asociados al usuario"
            />

            <div className="user-detail-credentials-grid">

              <CredentialCard
                icon={Mail}
                title="Cuenta Gmail"
                account={
                  usuario.gmail ||
                  'Sin cuenta Gmail'
                }
                password={usuario.password_gmail_configured ? '••••••••' : ''}
                onToggle={role === 'Administrador'
                  ? () => onRevealSecret?.({ module: 'usuario', object_id: usuario.id, secret_type: 'password_gmail' })
                  : undefined}
              />
              <CredentialCard
                icon={ShieldCheck}
                title="VPN Cisco"
                password={usuario.password_vpn_configured ? '••••••••' : ''}
                onToggle={role === 'Administrador'
                  ? () => onRevealSecret?.({ module: 'usuario', object_id: usuario.id, secret_type: 'password_vpn' })
                  : undefined}
              />

            </div>
          </section>


          {/* EQUIPOS */}

          <section className="user-detail-section">

            <SectionHeader
              title="Equipos Asignados"
              subtitle={`${usuario.equipos?.length || 0} ${usuario.equipos?.length === 1
                ? 'equipo vinculado'
                : 'equipos vinculados'
                }`}
            />

            {usuario.equipos &&
              usuario.equipos.length > 0 ? (

              <div className="user-detail-equipment-list">

                {usuario.equipos.map(
                  (equipo) => {
                    const tipoEquipo =
                      formatEquipmentType(
                        equipo.tipo
                      );

                    const EquipmentIcon =
                      getEquipmentIcon(
                        tipoEquipo
                      );

                    const normalizedEquipo = {
                      ...equipo,
                      tipo: tipoEquipo,
                    };

                    const identifier =
                      getEquipmentIdentifier(
                        normalizedEquipo
                      );

                    const identifierLabel =
                      getEquipmentIdentifierLabel(
                        tipoEquipo
                      );

                    return (
                      <article
                        key={equipo.id}
                        className="user-detail-equipment-card"
                      >

                        <div className="user-detail-equipment-header">

                          <div className="user-detail-equipment-identity">

                            <div className="user-detail-equipment-icon">
                              <EquipmentIcon
                                size={20}
                              />
                            </div>

                            <div>
                              <span className="user-detail-equipment-type">
                                {tipoEquipo}
                              </span>

                              <h4>
                                {`${equipo.marca || ''} ${equipo.modelo || ''
                                  }`.trim() ||
                                  'Sin marca / modelo'}
                              </h4>
                            </div>

                          </div>

                          <span className="user-detail-af">
                            AF: {equipo.af || 'N/I'}
                          </span>

                        </div>


                        <div className="user-detail-equipment-grid">

                          <EquipmentField
                            icon={Hash}
                            label="N° Serie"
                            value={
                              equipo.numero_serie ||
                              'N/I'
                            }
                          />

                          {identifierLabel && (
                            <EquipmentField
                              icon={
                                equipmentUsesHostname(
                                  tipoEquipo
                                )
                                  ? Monitor
                                  : Smartphone
                              }
                              label={
                                identifierLabel
                              }
                              value={
                                identifier ||
                                'N/A'
                              }
                              accent
                            />
                          )}

                          {tipoEquipo ===
                            'Celular' && (
                              <>
                                <EquipmentField
                                  icon={Smartphone}
                                  label="IMEI"
                                  value={
                                    equipo.imei ||
                                    'N/I'
                                  }
                                />

                                <EquipmentField
                                  icon={KeyRound}
                                  label="PIN"
                                  value={
                                    equipo.pin ||
                                    'N/I'
                                  }
                                />
                              </>
                            )}

                          {tipoEquipo ===
                            'Mac' && (
                              <EquipmentField
                                icon={Cloud}
                                label="Cuenta iCloud"
                                value={
                                  equipo
                                    .icloud_cuenta ||
                                  'N/I'
                                }
                              />
                            )}

                        </div>

                      </article>
                    );
                  }
                )}

              </div>

            ) : (

              <div className="user-detail-empty-equipment">
                <Cpu size={26} />

                <span>
                  Este usuario no tiene equipos vinculados.
                </span>

                <p id="acta-unavailable-reason">
                  {actaUnavailableMessage}
                </p>
              </div>

            )}

          </section>

        </div>
      </section>
    </div>
  );
}


/* =========================
   SECTION HEADER
========================= */

function SectionHeader({
  title,
  subtitle,
}) {
  return (
    <div className="user-detail-section-header">
      <h3>{title}</h3>

      {subtitle && (
        <p>{subtitle}</p>
      )}
    </div>
  );
}


/* =========================
   INFO CARD
========================= */

function InfoCard({
  icon: Icon,
  label,
  value,
  accent = false,
  compact = false,
}) {
  return (
    <div className="user-detail-info-card">

      <div className="user-detail-info-icon">
        <Icon size={18} />
      </div>

      <div className={`user-detail-info-text ${compact ? 'user-detail-info-text-compact' : ''}`}>
        <span className="user-detail-info-label">
          {label}
        </span>

        <span
          className={`user-detail-info-value ${accent
            ? 'user-detail-info-value-accent'
            : ''
            } ${compact
              ? 'user-detail-info-value-compact'
              : ''
            }`}
        >
          {value}
        </span>
      </div>

    </div>
  );
}


/* =========================
   CREDENTIAL CARD
========================= */

function CredentialCard({
  icon: Icon,
  title,
  account,
  password,
  onToggle,
}) {
  return (
    <div className="user-detail-credential-card">

      <div className="user-detail-credential-title">

        <div className="user-detail-credential-icon">
          <Icon size={17} />
        </div>

        <span>
          {title}
        </span>

      </div>

      {account && (
        <div className="user-detail-credential-account">
          {account}
        </div>
      )}

      <div className="user-detail-password-row">

        <span className="user-detail-password-value">
          {password ? '••••' : 'Sin contraseña'}
        </span>

        {password && onToggle && (
          <div className="user-detail-password-actions">

            <button
              type="button"
              onClick={onToggle}
              title="Revelar contraseña"
              aria-label={`Revelar contraseña de ${title}`}
            >
              <Eye size={16} />
            </button>

          </div>
        )}

      </div>

    </div>
  );
}


/* =========================
   EQUIPMENT FIELD
========================= */

function EquipmentField({
  icon: Icon,
  label,
  value,
  accent = false,
}) {
  return (
    <div className="user-detail-equipment-field">

      <Icon size={15} />

      <div>
        <span className="user-detail-equipment-field-label">
          {label}
        </span>

        <span
          className={`user-detail-equipment-field-value ${accent
            ? 'accent'
            : ''
            }`}
        >
          {value}
        </span>
      </div>

    </div>
  );
}
