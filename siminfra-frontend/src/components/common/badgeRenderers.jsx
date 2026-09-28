import StatusDot from './StatusDot';

const baseBadgeStyle = {
  padding: '0.3rem 0.75rem',
  borderRadius: '999px',
  fontSize: '0.75rem',
  fontWeight: 700,
  whiteSpace: 'nowrap',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '0.4rem',
};

export const renderUsuarioStatusBadge = (estado) => {
  switch (estado) {
    case 'LICENCIA':
      return (
        <span
          style={{
            ...baseBadgeStyle,
            backgroundColor: '#fef3c7',
            color: '#b45309',
          }}
        >
          <StatusDot />
          Licencia Médica
        </span>
      );

    case 'BAJA':
      return (
        <span
          style={{
            ...baseBadgeStyle,
            backgroundColor: '#fee2e2',
            color: '#b91c1c',
          }}
        >
          <StatusDot />
          Dar de Baja
        </span>
      );

    default:
      return (
        <span
          style={{
            ...baseBadgeStyle,
            backgroundColor: '#dcfce7',
            color: '#15803d',
          }}
        >
          <StatusDot />
          Activo
        </span>
      );
  }
};

export const renderAccountTypeBadge = (tipo) => {
  if (tipo === 'O365') {
    return (
      <span
        style={{
          ...baseBadgeStyle,
          backgroundColor: '#dbeafe',
          color: '#1d4ed8',
        }}
      >
        O365
      </span>
    );
  }

  return (
    <span
      style={{
        ...baseBadgeStyle,
        backgroundColor: '#f1f5f9',
        color: '#475569',
        border: '1px solid #cbd5e1',
      }}
    >
      On Premise
    </span>
  );
};

export const renderIpStatusBadge = (estado) => {
  switch (estado) {
    case 'LIBRE':
      return (
        <span
          style={{
            ...baseBadgeStyle,
            backgroundColor: '#dcfce7',
            color: '#15803d',
          }}
        >
          <StatusDot />
          Libre
        </span>
      );

    case 'RESERVADA':
      return (
        <span
          style={{
            ...baseBadgeStyle,
            backgroundColor: '#fee2e2',
            color: '#b91c1c',
          }}
        >
          <StatusDot />
          Reservada
        </span>
      );

    default:
      return (
        <span
          style={{
            ...baseBadgeStyle,
            backgroundColor: '#f1f5f9',
            color: '#475569',
          }}
        >
          Estado no válido
        </span>
      );
  }
};

export const renderAnexoStatusBadge = (estado) => {
  switch (estado) {
    case 'DISPONIBLE':
      return (
        <span
          style={{
            ...baseBadgeStyle,
            backgroundColor: '#dcfce7',
            color: '#15803d',
          }}
        >
          <StatusDot />
          Disponible
        </span>
      );

    case 'ASIGNADO':
      return (
        <span
          style={{
            ...baseBadgeStyle,
            backgroundColor: '#fee2e2',
            color: '#b91c1c',
          }}
        >
          <StatusDot />
          Asignado
        </span>
      );

    default:
      return (
        <span
          style={{
            ...baseBadgeStyle,
            backgroundColor: '#f1f5f9',
            color: '#475569',
          }}
        >
          Sin estado
        </span>
      );
  }
};
