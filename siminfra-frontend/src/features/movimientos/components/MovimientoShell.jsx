import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import '../../../components/common/CreateModal.css';
import './Movimientos.css';

export default function MovimientoShell({ title, onClose, busy = false, children, footer }) {
  const dialog = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    dialog.current?.focus();
    return () => previous?.focus();
  }, []);

  const handleKeyDown = (event) => {
    if (event.key !== 'Tab') return;
    const elements = dialog.current.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]');
    if (!elements.length) { event.preventDefault(); return; }
    const first = elements[0];
    const last = elements[elements.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.current)) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  };

  return (
    <div className="create-modal-overlay" onKeyDown={handleKeyDown}>
      <section className="create-modal movimiento-modal" role="dialog" aria-modal="true" aria-labelledby="movimiento-title" tabIndex={-1} ref={dialog}>
        <div className="create-modal-header">
          <h3 id="movimiento-title">{title}</h3>
          <button type="button" className="create-modal-close" onClick={onClose} disabled={busy} aria-label="Cerrar"><X size={20} /></button>
        </div>
        <div className="create-modal-content movimiento-content">{children}</div>
        {footer && <div className="create-modal-footer movimiento-footer">{footer}</div>}
      </section>
    </div>
  );
}
