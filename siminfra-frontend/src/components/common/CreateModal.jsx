import {
  X,
  Save
} from 'lucide-react';

import './CreateModal.css';

export default function CreateModal({
  title,
  onClose,
  onSubmit,
  children,
}) {
  return (
    <div
      className="create-modal-overlay"
      role="presentation"
    >
      <section
        className="create-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-modal-title"
      >
        {/* ENCABEZADO */}
        <div className="create-modal-header">
          <h3 id="create-modal-title">{title}</h3>

          <button
            type="button"
            onClick={onClose}
            className="create-modal-close"
            title="Cerrar"
            aria-label="Cerrar"
          >
            <X size={20} />
          </button>
        </div>

        {/* FORMULARIO */}
        <form
          onSubmit={onSubmit}
          className="create-modal-form"
        >
          <div className="create-modal-content">
            {children}
          </div>

          {/* BOTÓN FIJO ABAJO */}
          <div className="create-modal-footer">
            <button
              type="submit"
              className="create-modal-save"
            >
              <Save size={17} />

              <span>
                Guardar Nuevo Registro
              </span>
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
