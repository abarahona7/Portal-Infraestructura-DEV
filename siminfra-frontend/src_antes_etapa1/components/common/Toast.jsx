import {
  CheckCircle2,
  CircleAlert,
  Info,
  X
} from 'lucide-react';

import './Toast.css';

export default function Toast({
  message,
  type = 'success',
  onClose
}) {
  if (!message) {
    return null;
  }

  const icons = {
    success: CheckCircle2,
    error: CircleAlert,
    warning: CircleAlert,
    info: Info
  };

  const Icon = icons[type] || Info;

  return (
    <div className={`toast toast-${type}`}>
      <div className="toast-icon">
        <Icon size={21} />
      </div>

      <div className="toast-message">
        {message}
      </div>

      <button
        type="button"
        className="toast-close"
        onClick={onClose}
        aria-label="Cerrar notificación"
      >
        <X size={17} />
      </button>
    </div>
  );
}