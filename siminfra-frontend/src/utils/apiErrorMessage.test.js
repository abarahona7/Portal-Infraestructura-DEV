import { describe, expect, it } from 'vitest';

import { getApiErrorMessage, getApiErrorMessageAsync } from './apiErrorMessage';

describe('getApiErrorMessage', () => {
  it('muestra campo y restricción entregados por Django REST Framework', () => {
    const error = {
      response: {
        status: 400,
        data: {
          usuario: ['No se puede asignar un equipo a un usuario de baja.'],
        },
      },
    };

    expect(getApiErrorMessage(error)).toBe(
      'Usuario: No se puede asignar un equipo a un usuario de baja.'
    );
  });

  it('prioriza el detalle de un conflicto sin mostrar metadatos internos', () => {
    const error = {
      response: {
        status: 409,
        data: {
          detail: 'El registro fue actualizado por otra persona.',
          code: 'stale_update',
          current_version: '4',
        },
      },
    };

    expect(getApiErrorMessage(error)).toBe(
      'El registro fue actualizado por otra persona.'
    );
  });

  it('explica una falla de red', () => {
    expect(getApiErrorMessage({ code: 'ERR_NETWORK' })).toBe(
      'No se pudo conectar con el servidor. Revisa la red e inténtalo nuevamente.'
    );
  });

  it('explica permisos cuando la respuesta no trae detalle', () => {
    expect(getApiErrorMessage({ response: { status: 403, data: {} } })).toBe(
      'No tienes permisos para realizar esta operación.'
    );
  });

  it('oculta detalles técnicos en errores internos y conserva el código de soporte', () => {
    const error = {
      response: {
        status: 500,
        data: {
          detail: 'OperationalError: tabla_interna no existe',
          request_id: 'abc123',
        },
      },
    };

    expect(getApiErrorMessage(error)).toBe(
      'El servidor no pudo completar la operación. Código de soporte: abc123'
    );
  });

  it('lee el detalle JSON recibido como Blob al descargar un PDF', async () => {
    const error = {
      response: {
        status: 409,
        data: new Blob([
          JSON.stringify({ detail: 'El usuario no tiene equipos asignados.' }),
        ], { type: 'application/json' }),
      },
    };

    await expect(getApiErrorMessageAsync(error)).resolves.toBe(
      'El usuario no tiene equipos asignados.'
    );
  });
});
