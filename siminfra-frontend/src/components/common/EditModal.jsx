import { Save, X } from 'lucide-react';

import './EditModal.css';


export default function EditModal({
  title = 'Editar Registro',
  onClose,
  onSubmit,
  children,
}) {
  return (
    <div
      className="edit-modal-overlay"
      role="presentation"
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          onClose?.();
        }
      }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose?.();
        }
      }}
    >
      <section
        className="edit-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-modal-title"
      >
        <header className="edit-modal-header">
          <h3 id="edit-modal-title">{title}</h3>

          <button
            type="button"
            className="edit-modal-close"
            onClick={onClose}
            title="Cerrar"
            aria-label="Cerrar"
          >
            <X size={22} aria-hidden="true" />
          </button>
        </header>

        <form onSubmit={onSubmit} className="edit-modal-form">
          <div className="edit-modal-content">
            {children}
          </div>

          <footer className="edit-modal-footer">
            <button type="submit" className="edit-modal-save">
              <Save size={16} aria-hidden="true" />
              Guardar Cambios
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}
