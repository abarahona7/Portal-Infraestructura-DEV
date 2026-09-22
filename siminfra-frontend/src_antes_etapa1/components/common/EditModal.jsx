import {
  X,
  Save
} from 'lucide-react';

export default function EditModal({
  title = 'Editar Registro',
  onClose,
  onSubmit,
  children,
}) {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.55)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
        zIndex: 1000,
        boxSizing: 'border-box'
      }}
    >
      <div
        style={{
          backgroundColor: '#fff',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '560px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 20px 40px rgba(0,0,0,0.18)'
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1.25rem 1.25rem 1rem 1.25rem',
            borderBottom: '1px solid #e2e8f0',
            backgroundColor: '#fff',
            flexShrink: 0
          }}
        >
          <h3
            style={{
              margin: 0,
              color: '#0f172a',
              fontSize: '1.35rem',
              fontWeight: '800'
            }}
          >
            {title}
          </h3>

          <button
            type="button"
            onClick={onClose}
            style={{
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#334155',
              padding: '0.25rem'
            }}
            title="Cerrar"
          >
            <X size={22} />
          </button>
        </div>

        <form
          onSubmit={onSubmit}
          style={{
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
            flex: 1
          }}
        >
          {/* Contenido con scroll */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              padding: '1.25rem',
              overflowY: 'auto',
              flex: 1,
              minHeight: 0
            }}
          >
            {children}
          </div>

          {/* Footer fijo */}
          <div
            style={{
              padding: '1rem 1.25rem 1.25rem 1.25rem',
              borderTop: '1px solid #e2e8f0',
              backgroundColor: '#fff',
              flexShrink: 0
            }}
          >
            <button
              type="submit"
              style={{
                width: '100%',
                backgroundColor: '#2563eb',
                color: '#fff',
                border: 'none',
                padding: '0.85rem 1rem',
                borderRadius: '10px',
                cursor: 'pointer',
                fontWeight: '700',
                fontSize: '0.95rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem'
              }}
            >
              <Save size={16} />
              Guardar Cambios
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}