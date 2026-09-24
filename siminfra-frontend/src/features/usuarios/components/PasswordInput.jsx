import {
  Eye,
  EyeOff
} from 'lucide-react';

export default function PasswordInput({
  label,
  value,
  onChange,
  visible,
  onToggle,
}) {
  return (
    <div>
      <label
        style={{
          fontSize: '0.8rem',
          color: '#64748b',
          fontWeight: 'bold'
        }}
      >
        {label}
      </label>

      <div
        style={{
          position: 'relative',
          marginTop: '4px'
        }}
      >
        <input
          type={visible ? 'text' : 'password'}
          value={value || ''}
          onChange={(e) =>
            onChange(e.target.value)
          }
          style={{
            width: '100%',
            padding: '0.6rem',
            paddingRight: '2.5rem',
            borderRadius: '6px',
            border: '1px solid #cbd5e1',
            boxSizing: 'border-box'
          }}
        />

        <button
          type="button"
          onClick={onToggle}
          title={
            visible
              ? 'Ocultar contraseña'
              : 'Mostrar contraseña'
          }
          aria-label={
            visible
              ? `Ocultar ${label}`
              : `Mostrar ${label}`
          }
          style={{
            position: 'absolute',
            right: '0.2rem',
            top: '50%',
            transform: 'translateY(-50%)',
            border: 'none',
            background: 'transparent',
            cursor: 'pointer',
            color: '#64748b',
            width: '44px',
            height: '44px',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '0.4rem'
          }}
        >
          {visible ? (
            <EyeOff size={17} />
          ) : (
            <Eye size={17} />
          )}
        </button>
      </div>
    </div>
  );
}
