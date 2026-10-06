export const prepareCreatePayload = (
  tab,
  item
) => {
  const payload = { ...item };

  /* =========================
     CONVERTIR VACÍOS EN NULL
  ========================= */

  Object.keys(payload).forEach((key) => {
    if (payload[key] === '') {
      payload[key] = null;
    }
  });


  /* =========================
     USUARIOS
  ========================= */

  if (tab === 'usuarios') {
    // dpto_area queda como campo legado de compatibilidad.
    // El backend lo sincroniza desde la relación Departamento.
    delete payload.dpto_area;

    ['nombre_completo', 'usuario_red', 'correo_corp', 'cargo', 'hostname', 'celular', 'gmail'].forEach((field) => {
      if (typeof payload[field] === 'string') {
        payload[field] = payload[field].trim();
      }
    });

    if (payload.usuario_red) payload.usuario_red = payload.usuario_red.toLowerCase();
    if (payload.correo_corp) payload.correo_corp = payload.correo_corp.toLowerCase();
    if (payload.gmail) payload.gmail = payload.gmail.toLowerCase();
  }


  /* =========================
     EQUIPOS
  ========================= */

  if (tab === 'equipos') {
    ['marca', 'modelo', 'numero_serie', 'hostname', 'af', 'numero_telefono', 'imei', 'icloud_cuenta', 'accesorios'].forEach((field) => {
      if (typeof payload[field] === 'string') {
        payload[field] = payload[field].trim();
      }
    });

    if (!payload.numero_serie) payload.numero_serie = null;
    if (!payload.af) payload.af = null;
    if (!payload.hostname) payload.hostname = null;
    if (!payload.numero_telefono) payload.numero_telefono = null;
    if (!payload.imei) payload.imei = null;
    if (!payload.icloud_cuenta) payload.icloud_cuenta = null;
    if (!payload.accesorios) payload.accesorios = null;
    if (payload.icloud_cuenta) payload.icloud_cuenta = payload.icloud_cuenta.toLowerCase();
  }


  /* =========================
     PERFILES GENÉRICOS
  ========================= */

  if (tab === 'perfiles') {
    delete payload.dpto_area;

    if (payload.nombre) payload.nombre = payload.nombre.trim();
    if (payload.usuario) payload.usuario = payload.usuario.trim();
    if (payload.correo) payload.correo = payload.correo.trim();
    if (payload.observaciones) payload.observaciones = payload.observaciones.trim();

    payload.estado = payload.estado || 'ACTIVO';
  }


  /* =========================
     IPS
  ========================= */

  if (tab === 'ips') {
    // La asignación a usuarios solo se administra desde Usuarios.
    delete payload.usuario;

    // LIBRE / RESERVADA se calcula automáticamente en backend.
    delete payload.estado;

    if (payload.asignado_otro) {
      payload.asignado_otro = payload.asignado_otro.trim() || null;
    }

    if (payload.observacion) {
      payload.observacion = payload.observacion.trim() || null;
    }
  }


  /* =========================
     ANEXOS
  ========================= */

  if (tab === 'anexos') {
    // El estado lo administra el backend
    delete payload.estado;

    if (payload.numero_anexo) {
      payload.numero_anexo =
        payload.numero_anexo.trim();
    }

    if (payload.exterior) {
      payload.exterior =
        payload.exterior.trim();
    }

    if (payload.observaciones) {
      payload.observaciones =
        payload.observaciones.trim();
    }
  }


  /* =========================
     PCS GENERICOS
  ========================= */

  if (tab === 'pcs-genericos') {
    if (payload.usuario_local) {
      payload.usuario_local =
        payload.usuario_local.trim();
    }

    if (payload.hostname) {
      payload.hostname =
        payload.hostname.trim();
    }

    delete payload.dpto_area;

    if (payload.marca) {
      payload.marca =
        payload.marca.trim();
    }

    if (payload.modelo) {
      payload.modelo =
        payload.modelo.trim();
    }

    if (payload.numero_serie) {
      payload.numero_serie =
        payload.numero_serie.trim();
    }

    if (payload.activo_fijo) {
      payload.activo_fijo =
        payload.activo_fijo.trim();
    }

    if (payload.observaciones) {
      payload.observaciones =
        payload.observaciones.trim();
    }
  }


  /* =========================
     SERVIDORES
  ========================= */

  if (tab === 'servidores') {
    if (payload.ip) {
      payload.ip =
        payload.ip.trim();
    }

    if (payload.hostname) {
      payload.hostname =
        payload.hostname.trim();
    }

    if (payload.descripcion) {
      payload.descripcion =
        payload.descripcion.trim();
    }
  }


  return payload;
};
