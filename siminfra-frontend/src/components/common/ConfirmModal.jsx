import {
  CircleAlert,
  X
} from 'lucide-react';
import { useState } from 'react';

import './ConfirmModal.css';

export default function ConfirmModal({
  open,
  title = 'Confirmar acción',
  message,
  confirmText = 'Confirmar',
  cancelText = 'Cancelar',
  danger = false,
  checklist = [],
  onConfirm,
  onCancel,
}) {
  const [checked, setChecked] = useState([]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="confirm-overlay"
      role="presentation"
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          onCancel?.();
        }
      }}
    >
      <section
        className="confirm-modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
        aria-describedby="confirm-modal-message"
      >
        <button
          type="button"
          className="confirm-close"
          onClick={onCancel}
          aria-label="Cerrar"
        >
          <X size={18} />
        </button>

        <div
          className={
            danger
              ? 'confirm-icon confirm-icon-danger'
              : 'confirm-icon'
          }
        >
          <CircleAlert size={28} />
        </div>

        <h3 id="confirm-modal-title" className="confirm-title">
          {title}
        </h3>

        <p id="confirm-modal-message" className="confirm-message">
          {message}
        </p>

        {checklist.length > 0 && (
          <div className="confirm-checklist" role="group" aria-label="Protocolo de confirmación">
            {checklist.map(({ id, label }) => (
              <label key={id} className="confirm-checklist-item">
                <input
                  type="checkbox"
                  checked={checked.includes(id)}
                  onChange={(event) => setChecked((current) => (
                    event.target.checked ? [...current, id] : current.filter((item) => item !== id)
                  ))}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        )}

        <div className="confirm-actions">
          <button
            type="button"
            className="confirm-button confirm-button-cancel"
            onClick={onCancel}
          >
            {cancelText}
          </button>

          <button
            type="button"
            className={
              danger
                ? 'confirm-button confirm-button-danger'
                : 'confirm-button confirm-button-primary'
            }
            onClick={() => onConfirm?.(checked)}
            disabled={checklist.length > 0 && checked.length !== checklist.length}
          >
            {confirmText}
          </button>
        </div>
      </section>
    </div>
  );
}
