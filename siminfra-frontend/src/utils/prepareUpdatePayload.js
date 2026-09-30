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
  delete payload.password_configured;


  /* =========================
     USUARIOS
  ========================= */

  if (tab === 'usuarios') {
    delete payload.celular;
    delete payload.dpto_area;

    ['nombre_completo', 'usuario_red', 'correo_corp', 'cargo', 'hostname', 'gmail'].forEach((field) => {
      if (typeof payload[field] === 'string') {
        payload[field] = payload[field].trim();
      }
    });

    if (payload.usuario_red) payload.usuario_red = payload.usuario_red.toLowerCase();
    if (payload.correo_corp) payload.correo_corp = payload.correo_corp.toLowerCase();
    if (payload.gmail) payload.gmail = payload.gmail.toLowerCase();

    if (payload.ip_seleccionada === '') {
      payload.ip_seleccionada = null;
    }
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
    delete payload.usuario;
    delete payload.estado;
    delete payload.estado_fisico;
    delete payload.ubicacion_actual;
    delete payload.fecha_asignacion;
    delete payload.accesorios_requeridos;
    delete payload.token_qr;
    delete payload.fecha_alta;
    ['marca', 'modelo', 'numero_serie', 'hostname', 'af', 'numero_telefono', 'imei', 'mac_address', 'icloud_cuenta', 'accesorios'].forEach((field) => {
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

    delete payload.dpto_area;

    if (payload.marca) {
      payload.marca =
        payload.marca.trim();
    }

    if (payload.modelo) {
      payload.modelo =
        payload.modelo.trim();
    }

    if (typeof payload.numero_serie === 'string') {
      payload.numero_serie = payload.numero_serie.trim() || null;
    }

    if (typeof payload.activo_fijo === 'string') {
      payload.activo_fijo = payload.activo_fijo.trim() || null;
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
