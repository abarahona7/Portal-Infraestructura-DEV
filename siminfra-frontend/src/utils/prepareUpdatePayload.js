export const prepareUpdatePayload = (
  tab,
  item,
  formatTipoEquipo
) => {
  const payload = { ...item };

  /* =========================
     CAMPOS GENERALES
     SOLO LECTURA / NO ENVIAR
  ========================= */

  delete payload.equipos;
  delete payload.historial;
  delete payload.id;
  delete payload.usuario_nombre;
  delete payload.ip_actual;
  delete payload.departamento_nombre;
  delete payload.subarea_nombre;
  delete payload.anexo_actual;
  delete payload.password_gmail_configured;
  delete payload.password_vpn_configured;


  /* =========================
     USUARIOS
  ========================= */

  if (tab === 'usuarios') {
    delete payload.celular;
    delete payload.dpto_area;

    if (payload.ip_seleccionada === '') {
      payload.ip_seleccionada = null;
    }
  }


  /* =========================
     EQUIPOS
     NORMALIZAR TIPO
  ========================= */

  if (
    tab === 'equipos' &&
    payload.tipo
  ) {
    payload.tipo =
      formatTipoEquipo(payload.tipo);
  }


  /* =========================
     EQUIPOS
     USUARIO / ESTADO
  ========================= */

  if (tab === 'equipos') {
    if (!payload.usuario) {
      payload.estado = 'STOCK';
      payload.fecha_asignacion = null;
    } else if (
      payload.estado === 'STOCK'
    ) {
      payload.estado = 'ASIGNADO';
    }
  }


  /* =========================
     ANEXOS
  ========================= */

  if (tab === 'anexos') {
    // Datos provenientes del usuario relacionado
    delete payload.departamento;
    delete payload.cargo;
    delete payload.correo;

    // Backend administra estado
    delete payload.estado;

    // Django administra fechas
    delete payload.fecha_creacion;
    delete payload.fecha_actualizacion;

    if (!payload.usuario) {
      payload.usuario = null;
    }

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
     NORMALIZAR ESTADOS
  ========================= */

  if (
    payload.estado &&
    tab !== 'ips' &&
    tab !== 'anexos'
  ) {
    payload.estado =
      payload.estado.toUpperCase();
  }


  /* =========================
     PCS GENERICOS
  ========================= */

  if (tab === 'pcs-genericos') {
    delete payload.fecha_creacion;
    delete payload.fecha_actualizacion;

    if (payload.usuario_local) {
      payload.usuario_local =
        payload.usuario_local.trim();
    }

    if (payload.hostname) {
      payload.hostname =
        payload.hostname.trim();
    }

    if (payload.dpto_area) {
      payload.dpto_area =
        payload.dpto_area.trim();
    }

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

    if (!payload.descripcion) {
      payload.descripcion = null;
    }
  }


  /* =========================
     IPS
  ========================= */

  if (tab === 'ips') {
    // Nunca modificar la relación con Usuario desde Gestión IPs.
    delete payload.usuario;

    // El backend deriva el estado desde usuario/asignado_otro.
    delete payload.estado;

    if (payload.asignado_otro) {
      payload.asignado_otro = payload.asignado_otro.trim() || null;
    }

    if (payload.observacion) {
      payload.observacion = payload.observacion.trim() || null;
    }
  }

  return payload;
};