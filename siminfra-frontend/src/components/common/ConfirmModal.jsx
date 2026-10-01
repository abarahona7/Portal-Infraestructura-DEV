import {
  CircleAlert,
  X
} from 'lucide-react';

import './ConfirmModal.css';

export default function ConfirmModal({
  open,
  title = 'Confirmar acción',
  message,
  confirmText = 'Confirmar',
  cancelText = 'Cancelar',
  danger = false,
  onConfirm,
  onCancel,
}) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="confirm-overlay"
      role="presentation"
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
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </section>
    </div>
  );
}
