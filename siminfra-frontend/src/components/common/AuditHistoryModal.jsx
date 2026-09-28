import { useEffect, useState } from 'react';
import {
  CalendarClock,
  ChevronDown,
  ChevronUp,
  Download,
  History,
  UserRound,
  X,
} from 'lucide-react';

import './AuditHistoryModal.css';

const parseDetails = (observacion) => {
  if (!observacion || !observacion.includes(':::')) {
    return [];
  }

  return observacion
    .split('||')
    .map((item) => {
      const [campo, anterior, actual] = item.split(':::');
      return {
        campo: campo || 'Campo',
        anterior: anterior || 'N/I',
        actual: actual || 'N/I',
      };
    });
};

export default function AuditHistoryModal({
  open,
  title,
  subtitle,
  entries = [],
  emptyMessage,
  onClose,
  getMetaRows,
  onExport,
  exportLabel = 'Exportar Excel',
}) {
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    if (!open) {
      setExpanded({});
      return undefined;
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose?.();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="audit-history-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose?.();
        }
      }}
    >
      <section
        className="audit-history-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="audit-history-header">
          <div className="audit-history-heading">
            <span className="audit-history-heading-icon">
              <History size={21} />
            </span>

            <div>
              <h3>{title}</h3>
              {subtitle && <p>{subtitle}</p>}
            </div>
          </div>

          <div className="audit-history-header-actions">
            {onExport && (
              <button
                type="button"
                className="audit-history-export"
                onClick={onExport}
              >
                <Download size={17} />
                <span>{exportLabel}</span>
              </button>
            )}

            <button
              type="button"
              className="audit-history-close"
              onClick={onClose}
              aria-label="Cerrar historial"
              title="Cerrar"
            >
              <X size={20} />
            </button>
          </div>
        </header>

        <div className="audit-history-body">
          {entries.length === 0 ? (
            <div className="audit-history-empty">
              <span className="audit-history-empty-icon">
                <History size={24} />
              </span>
              <p>{emptyMessage}</p>
            </div>
          ) : (
            <div className="audit-history-timeline">
              {entries.map((entry, index) => {
                const entryKey = entry.id || index;
                const isExpanded = Boolean(expanded[entryKey]);
                const details = parseDetails(entry.observacion);
                const metaRows = getMetaRows?.(entry) || [];
                const hasDetails = details.length > 0 || Boolean(entry.observacion);

                return (
                  <article
                    key={entryKey}
                    className="audit-history-entry"
                  >
                    <span className="audit-history-dot" />

                    <div className="audit-history-entry-top">
                      <span className="audit-history-action">
                        {entry.accion || 'MODIFICACIÓN'}
                      </span>

                      <span className="audit-history-date">
                        <CalendarClock size={14} />
                        {entry.fecha_movimiento
                          ? new Date(entry.fecha_movimiento).toLocaleString('es-CL')
                          : 'Fecha no registrada'}
                      </span>
                    </div>

                    <div className="audit-history-author">
                      <UserRound size={15} />
                      <span>Realizado por</span>
                      <strong>{entry.modificado_por || 'No registrado'}</strong>
                    </div>

                    {metaRows.length > 0 && (
                      <div className="audit-history-meta-grid">
                        {metaRows.map((row, metaIndex) => (
                          <div
                            key={`${entryKey}-${metaIndex}`}
                            className="audit-history-meta-item"
                          >
                            <span>{row.label}</span>
                            <strong>{row.value || 'N/I'}</strong>
                          </div>
                        ))}
                      </div>
                    )}

                    {hasDetails && (
                      <button
                        type="button"
                        className="audit-history-toggle"
                        onClick={() =>
                          setExpanded((prev) => ({
                            ...prev,
                            [entryKey]: !prev[entryKey],
                          }))
                        }
                      >
                        {isExpanded ? (
                          <ChevronUp size={16} />
                        ) : (
                          <ChevronDown size={16} />
                        )}

                        {isExpanded ? 'Ocultar detalles' : 'Ver detalles'}
                      </button>
                    )}

                    {isExpanded && (
                      <div className="audit-history-details">
                        {details.length > 0 ? (
                          details.map((detail, detailIndex) => (
                            <div
                              key={`${entryKey}-detail-${detailIndex}`}
                              className="audit-history-change-card"
                            >
                              <div className="audit-history-field-name">
                                {detail.campo}
                              </div>

                              <div className="audit-history-values">
                                <div className="audit-history-value audit-history-value-before">
                                  <span>Anterior</span>
                                  <strong>{detail.anterior}</strong>
                                </div>

                                <div className="audit-history-arrow" aria-hidden="true">
                                  →
                                </div>

                                <div className="audit-history-value audit-history-value-after">
                                  <span>Actual</span>
                                  <strong>{detail.actual}</strong>
                                </div>
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="audit-history-note">
                            {entry.observacion || 'Sin detalles adicionales.'}
                          </div>
                        )}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
