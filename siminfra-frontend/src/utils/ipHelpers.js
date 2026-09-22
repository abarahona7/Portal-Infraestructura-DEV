/* =========================
   SANITIZAR IP
========================= */

export const sanitizeIpInput = (value) => {
  return value.replace(/[^0-9.]/g, '');
};


/* =========================
   IPs DISPONIBLES
========================= */

export const getAvailableIpsForUser = (
  ipsList = [],
  currentIp
) => {
  return ipsList.filter(
    (ip) =>
      isManagedIpAddress(ip.direccion_ip) &&
      (
        ip.estado === 'LIBRE' ||
        ip.direccion_ip === currentIp
      )
  );
};


/* =========================
   SEGMENTOS DE REP
========================= */

export const IP_SEGMENTS = [
  {
    id: '172.23',
    label: '172.23.1.0/24',
    network: 'Vlan (10)',
    prefix: '172.23.1.',
  },
  {
    id: '172.24',
    label: '172.24.1.0/24',
    network: 'Vlan (11)',
    prefix: '172.24.1.',
  },
  {
    id: '172.25',
    label: '172.25.1.0/24',
    network: 'Vlan (9)',
    prefix: '172.25.1.',
  },
  {
    id: '192.168.10',
    label: '192.168.10.0/24',
    network: 'Vlan (12)',
    prefix: '192.168.10.',
  },
  {
    id: '192.168.20',
    label: '192.168.20.0/24',
    network: 'Vlan (20)',
    prefix: '192.168.20.',
  },
  {
    id: '192.168.30',
    label: '192.168.30.0/24',
    network: 'Vlan (30)',
    prefix: '192.168.30.',
  },
  {
    id: '192.168.90',
    label: '192.168.90.0/24',
    network: 'Vlan (90)',
    prefix: '192.168.90.',
  },
];


/* =========================
   OBTENER SEGMENTO DE UNA IP
========================= */

export const getIpSegment = (
  direccionIp = ''
) => {
  const ip = direccionIp.trim();

  const segment = IP_SEGMENTS.find(
    (item) =>
      ip.startsWith(item.prefix)
  );

  return segment || null;
};


/* =========================
   VALIDAR IP ADMINISTRADA
========================= */

export const isManagedIpAddress = (direccionIp = '') => {
  const ip = direccionIp.trim();
  const segment = getIpSegment(ip);

  if (!segment) {
    return false;
  }

  const parts = ip.split('.');
  if (parts.length !== 4) {
    return false;
  }

  const host = Number(parts[3]);
  return Number.isInteger(host) && host >= 1 && host <= 254;
};


/* =========================
   FILTRAR POR SEGMENTO
========================= */

export const filterIpsBySegment = (
  ips = [],
  selectedSegment
) => {
  if (!selectedSegment) {
    return ips;
  }

  const segment = IP_SEGMENTS.find(
    (item) =>
      item.id === selectedSegment
  );

  if (!segment) {
    return ips;
  }

  return ips.filter((ip) =>
    ip.direccion_ip
      ?.trim()
      .startsWith(segment.prefix)
  );
};


/* =========================
   CONTAR IPs POR SEGMENTO
========================= */

export const countIpsBySegment = (
  ips = [],
  segmentId
) => {
  const segment = IP_SEGMENTS.find(
    (item) =>
      item.id === segmentId
  );

  if (!segment) {
    return 0;
  }

  return ips.filter((ip) =>
    ip.direccion_ip
      ?.trim()
      .startsWith(segment.prefix)
  ).length;
};


/* =========================
   CONTADORES DE ESTADO
========================= */

export const getIpSegmentStats = (
  ips = [],
  segmentId
) => {
  const segmentIps =
    filterIpsBySegment(
      ips,
      segmentId
    );

  return {
    total: segmentIps.length,

    libres: segmentIps.filter(
      (ip) =>
        ip.estado === 'LIBRE'
    ).length,

    reservadas: segmentIps.filter(
      (ip) =>
        ip.estado === 'RESERVADA'
    ).length,
  };
};