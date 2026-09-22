import { useState } from 'react';

import {
  Eye,
  EyeOff,
  LogIn,
  User,
  Lock
} from 'lucide-react';

import './LoginPage.css';

export default function LoginPage({
  username,
  password,
  loginError,
  onUsernameChange,
  onPasswordChange,
  onSubmit,
}) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="login-page">
      <div className="login-background-decoration login-decoration-one" />
      <div className="login-background-decoration login-decoration-two" />

      <form
        onSubmit={onSubmit}
        className="login-card"
      >
        {/* LOGO / IDENTIDAD */}
        <div className="login-brand">
          <div className="login-logo">
            <img
              src="/branding/dr-simi-logo.png"
              alt="Farmacias Dr. Simi"
            />
          </div>

          <div className="login-brand-text">
            <span className="login-company">
              Farmacias Dr. Simi
            </span>

            <h1>
              Portal Infraestructura TI Chile
            </h1>

            <p>
              Panel Administrador de Infraestructura y Redes
            </p>
          </div>
        </div>

        {/* SEPARADOR */}
        <div className="login-divider" />

        {/* ENCABEZADO FORMULARIO */}
        <div className="login-form-header">
          <h2>Iniciar Sesión</h2>

          <p>
            Ingresa tus credenciales para acceder al portal.
          </p>
        </div>

        {/* ERROR */}
        {loginError && (
          <div className="login-error">
            {loginError}
          </div>
        )}

        {/* USUARIO */}
        <div className="login-field">
          <label htmlFor="login-username">
            Usuario
          </label>

          <div className="login-input-wrapper">
            <User
              size={18}
              className="login-input-icon"
            />

            <input
              id="login-username"
              type="text"
              required
              autoComplete="username"
              value={username}
              onChange={(e) =>
                onUsernameChange(e.target.value)
              }
              placeholder="Ingresa tu usuario"
            />
          </div>
        </div>

        {/* CONTRASEÑA */}
        <div className="login-field">
          <label htmlFor="login-password">
            Contraseña
          </label>

          <div className="login-input-wrapper">
            <Lock
              size={18}
              className="login-input-icon"
            />

            <input
              id="login-password"
              type={
                showPassword
                  ? 'text'
                  : 'password'
              }
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) =>
                onPasswordChange(e.target.value)
              }
              placeholder="Ingresa tu contraseña"
              className="login-password-input"
            />

            <button
              type="button"
              className="login-password-toggle"
              onClick={() =>
                setShowPassword((prev) => !prev)
              }
              title={
                showPassword
                  ? 'Ocultar contraseña'
                  : 'Mostrar contraseña'
              }
              aria-label={
                showPassword
                  ? 'Ocultar contraseña'
                  : 'Mostrar contraseña'
              }
            >
              {showPassword ? (
                <EyeOff size={18} />
              ) : (
                <Eye size={18} />
              )}
            </button>
          </div>
        </div>

        {/* INGRESAR */}
        <button
          type="submit"
          className="login-submit"
        >
          <LogIn size={18} />

          <span>
            Ingresar al Portal
          </span>
        </button>
      </form>
    </div>
  );
}