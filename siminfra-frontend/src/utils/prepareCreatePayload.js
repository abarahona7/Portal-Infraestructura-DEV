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
     IPS
  ========================= */

  if (tab === 'ips') {
    const tieneAsignacion =
      payload.usuario ||
      (
        payload.asignado_otro &&
        payload.asignado_otro.trim()
      );

    // Si tiene asignación y está LIBRE,
    // automáticamente pasa a RESERVADA.
    if (
      tieneAsignacion &&
      payload.estado === 'LIBRE'
    ) {
      payload.estado = 'RESERVADA';
    }

    // Si se elimina la asignación y estaba
    // RESERVADA, vuelve automáticamente a LIBRE.
    if (
      !tieneAsignacion &&
      payload.estado === 'RESERVADA'
    ) {
      payload.estado = 'LIBRE';
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
  }


  return payload;
};