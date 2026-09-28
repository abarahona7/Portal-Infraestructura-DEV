import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Eye,
  EyeOff,
  KeyRound,
  LockKeyhole,
  ShieldCheck,
  X,
} from 'lucide-react';

import apiClient from '../../api/client';
import './SecretRevealModal.css';

export default function SecretRevealModal({ request, username, onClose }) {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [secret, setSecret] = useState('');
  const [error, setError] = useState('');
  const [seconds, setSeconds] = useState(30);
  const [loading, setLoading] = useState(false);
  const passwordRef = useRef(null);

  const closeModal = useCallback(() => {
    setSecret('');
    setPassword('');
    setError('');
    setSeconds(30);
    onClose?.();
  }, [onClose]);

  useEffect(() => {
    passwordRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        closeModal();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [closeModal]);

  useEffect(() => {
    if (!secret) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setSeconds((current) => {
        if (current <= 1) {
          window.clearInterval(timer);
          setSecret('');
          onClose?.();
          return 30;
        }

        return current - 1;
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [secret, onClose]);

  const reveal = async (event) => {
    event.preventDefault();

    if (loading) {
      return;
    }

    setError('');
    setLoading(true);

    try {
      const { data } = await apiClient.post('/secrets/reveal/', {
        ...request,
        password,
      });

      setPassword('');
      setShowPassword(false);
      setSeconds(30);
      setSecret(data.secret || '');
    } catch (err) {
      setSecret('');
      setError(
        err?.response?.data?.detail ||
        'No fue posible revelar el secreto. Verifica tu contraseña e inténtalo nuevamente.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="secret-reveal-overlay"
      onMouseDown={closeModal}
      role="presentation"
    >
      <div
        className="secret-reveal-modal"
        onMouseDown={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="secret-reveal-title"
      >
        <button
          type="button"
          className="secret-reveal-close"
          onClick={closeModal}
          aria-label="Cerrar"
        >
          <X size={18} />
        </button>

        {!secret ? (
          <>
            <div className="secret-reveal-icon">
              <ShieldCheck size={28} />
            </div>

            <div className="secret-reveal-heading">
              <h3 id="secret-reveal-title">Confirmar identidad</h3>
              <p>
                Por seguridad, vuelve a ingresar tu contraseña de sesión antes de mostrar esta credencial.
              </p>
            </div>

            <form className="secret-reveal-form" onSubmit={reveal}>
              <label className="secret-reveal-field">
                <span>Usuario autenticado</span>
                <div className="secret-reveal-input-wrap secret-reveal-input-locked">
                  <LockKeyhole size={17} />
                  <input
                    value={username}
                    type="text"
                    readOnly
                    tabIndex={-1}
                    aria-readonly="true"
                  />
                </div>
              </label>

              <label className="secret-reveal-field">
                <span>Contraseña de sesión</span>
                <div className="secret-reveal-input-wrap">
                  <KeyRound size={17} />
                  <input
                    ref={passwordRef}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="Ingresa tu contraseña"
                    required
                    disabled={loading}
                  />
                  <button
                    type="button"
                    className="secret-reveal-password-toggle"
                    onClick={() => setShowPassword((current) => !current)}
                    aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    title={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  >
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>
              </label>

              {error && (
                <div className="secret-reveal-error" role="alert">
                  {error}
                </div>
              )}

              <div className="secret-reveal-actions">
                <button
                  type="button"
                  className="secret-reveal-button secret-reveal-button-secondary"
                  onClick={closeModal}
                  disabled={loading}
                >
                  Cancelar
                </button>

                <button
                  type="submit"
                  className="secret-reveal-button secret-reveal-button-primary"
                  disabled={loading || !password}
                >
                  {loading ? 'Verificando…' : 'Confirmar y revelar'}
                </button>
              </div>
            </form>
          </>
        ) : (
          <>
            <div className="secret-reveal-icon secret-reveal-icon-success">
              <Eye size={28} />
            </div>

            <div className="secret-reveal-heading">
              <h3 id="secret-reveal-title">Credencial revelada</h3>
              <p>
                Se ocultará automáticamente al finalizar el contador o al cerrar esta ventana.
              </p>
            </div>

            <div className="secret-reveal-result" aria-live="polite">
              <div className="secret-reveal-result-header">
                <span>Secreto</span>
                <span className="secret-reveal-countdown">
                  {seconds}s
                </span>
              </div>

              <div className="secret-reveal-secret-value">
                {secret}
              </div>
            </div>

            <div className="secret-reveal-security-note">
              <ShieldCheck size={16} />
              <span>La credencial no se guarda en esta ventana al cerrarla.</span>
            </div>

            <div className="secret-reveal-actions secret-reveal-actions-single">
              <button
                type="button"
                className="secret-reveal-button secret-reveal-button-primary"
                onClick={closeModal}
              >
                Ocultar ahora
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
