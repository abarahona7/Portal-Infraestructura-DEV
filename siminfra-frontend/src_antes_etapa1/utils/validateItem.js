const isValidIPv4 = (value = '') => {
  const parts = value.trim().split('.');

  if (parts.length !== 4) {
    return false;
  }

  return parts.every((part) => {
    if (!/^\d+$/.test(part)) {
      return false;
    }

    const number = Number(part);

    return (
      number >= 0 &&
      number <= 255
    );
  });
};


export const validateItem = (
  tab,
  item,
  data = []
) => {

  /* =========================
     IPS
  ========================= */

  if (tab === 'ips') {
    const direccionIp =
      (item.direccion_ip || '').trim();

    if (!isValidIPv4(direccionIp)) {
      return {
        valid: false,
        message:
          'Por favor ingrese una dirección IP válida (ejemplo: 192.168.1.50).',
      };
    }

    const dupIP = data.find(
      (ip) =>
        ip.id !== item.id &&
        ip.direccion_ip?.trim() ===
          direccionIp
    );

    if (dupIP) {
      return {
        valid: false,
        message:
          `Error: La dirección IP "${direccionIp}" ya existe en el sistema.`,
      };
    }
  }


  /* =========================
     SERVIDORES
  ========================= */

  if (tab === 'servidores') {
    const ip =
      (item.ip || '').trim();

    const hostname =
      (item.hostname || '').trim();

    /* IP obligatoria */

    if (!ip) {
      return {
        valid: false,
        message:
          'Debe ingresar la dirección IP del servidor.',
      };
    }

    /* IP IPv4 válida */

    if (!isValidIPv4(ip)) {
      return {
        valid: false,
        message:
          'Ingrese una dirección IPv4 válida (ejemplo: 172.23.10.15).',
      };
    }

    /* IP duplicada dentro de Servidores */

    const dupIpServidor = data.find(
      (servidor) =>
        servidor.id !== item.id &&
        servidor.ip?.trim() === ip
    );

    if (dupIpServidor) {
      return {
        valid: false,
        message:
          `Error: La IP "${ip}" ya está registrada en otro servidor.`,
      };
    }

    /* Hostname obligatorio */

    if (!hostname) {
      return {
        valid: false,
        message:
          'Debe ingresar el Hostname del servidor.',
      };
    }

    /* Largo Hostname */

    if (hostname.length > 100) {
      return {
        valid: false,
        message:
          'El Hostname puede tener como máximo 100 caracteres.',
      };
    }

    /* Hostname duplicado */

    const dupHostnameServidor = data.find(
      (servidor) =>
        servidor.id !== item.id &&
        servidor.hostname
          ?.trim()
          .toLowerCase() ===
          hostname.toLowerCase()
    );

    if (dupHostnameServidor) {
      return {
        valid: false,
        message:
          `Error: El Hostname "${hostname}" ya está registrado en otro servidor.`,
      };
    }
  }


  /* =========================
     ANEXOS
  ========================= */

  if (tab === 'anexos') {
    const numeroAnexo =
      (item.numero_anexo || '').trim();

    if (!numeroAnexo) {
      return {
        valid: false,
        message:
          'Debe ingresar un número de anexo.',
      };
    }

    if (!/^\d+$/.test(numeroAnexo)) {
      return {
        valid: false,
        message:
          'El número de anexo debe contener solo números.',
      };
    }

    if (numeroAnexo.length > 10) {
      return {
        valid: false,
        message:
          'El número de anexo puede tener como máximo 10 dígitos.',
      };
    }

    const dupAnexo = data.find(
      (anexo) =>
        anexo.id !== item.id &&
        anexo.numero_anexo?.trim() ===
          numeroAnexo
    );

    if (dupAnexo) {
      return {
        valid: false,
        message:
          `Error: El anexo "${numeroAnexo}" ya existe en el sistema.`,
      };
    }

    if (item.usuario) {
      const dupUsuario = data.find(
        (anexo) =>
          anexo.id !== item.id &&
          Number(anexo.usuario) ===
            Number(item.usuario)
      );

      if (dupUsuario) {
        return {
          valid: false,
          message:
            `Error: Este usuario ya tiene asignado el anexo "${dupUsuario.numero_anexo}".`,
        };
      }
    }
  }


  /* =========================
     PCS GENERICOS
  ========================= */

  if (tab === 'pcs-genericos') {
    const usuarioLocal =
      (item.usuario_local || '').trim();

    const hostname =
      (item.hostname || '').trim();

    if (!usuarioLocal) {
      return {
        valid: false,
        message:
          'Debe ingresar el Usuario Local del PC Genérico.',
      };
    }

    if (usuarioLocal.length > 150) {
      return {
        valid: false,
        message:
          'El Usuario Local puede tener como máximo 150 caracteres.',
      };
    }

    if (!hostname) {
      return {
        valid: false,
        message:
          'Debe ingresar el Hostname del PC Genérico.',
      };
    }

    if (hostname.length > 100) {
      return {
        valid: false,
        message:
          'El Hostname puede tener como máximo 100 caracteres.',
      };
    }

    const dupHostname = data.find(
      (pc) =>
        pc.id !== item.id &&
        pc.hostname
          ?.trim()
          .toLowerCase() ===
          hostname.toLowerCase()
    );

    if (dupHostname) {
      return {
        valid: false,
        message:
          `Error: El Hostname "${hostname}" ya está registrado en otro PC Genérico.`,
      };
    }
  }


  /* =========================
     ACTIVO FIJO
  ========================= */

  if (item.af) {
    if (item.af.trim().length > 12) {
      return {
        valid: false,
        message:
          'El Activo Fijo (AF) puede tener máximo 12 caracteres.',
      };
    }
  }


  /* =========================
     USUARIOS
  ========================= */

  if (tab === 'usuarios') {
    const dupNombre = data.find(
      (usuario) =>
        usuario.id !== item.id &&
        usuario.nombre_completo
          ?.trim()
          .toLowerCase() ===
        (item.nombre_completo || '')
          .trim()
          .toLowerCase()
    );

    if (dupNombre) {
      return {
        valid: false,
        message:
          `Error: Ya existe un usuario llamado "${item.nombre_completo}".`,
      };
    }

    const dupRed = data.find(
      (usuario) =>
        usuario.id !== item.id &&
        usuario.usuario_red
          ?.trim()
          .toLowerCase() ===
        (item.usuario_red || '')
          .trim()
          .toLowerCase()
    );

    if (dupRed) {
      return {
        valid: false,
        message:
          `Error: El usuario de red "${item.usuario_red}" ya existe.`,
      };
    }
  }


  /* =========================
     EQUIPOS
  ========================= */

  if (tab === 'equipos') {
    const numeroSerie =
      (item.numero_serie || '').trim();

    if (numeroSerie) {
      const dupSerie = data.find(
        (equipo) =>
          equipo.id !== item.id &&
          equipo.numero_serie
            ?.trim()
            .toLowerCase() ===
          numeroSerie.toLowerCase()
      );

      if (dupSerie) {
        return {
          valid: false,
          message:
            `Error: El número de serie "${numeroSerie}" ya está registrado.`,
        };
      }
    }

    if (item.af) {
      const dupAF = data.find(
        (equipo) =>
          equipo.id !== item.id &&
          equipo.af === item.af
      );

      if (dupAF) {
        return {
          valid: false,
          message:
            `Error: El Activo Fijo (AF) "${item.af}" ya pertenece a otro equipo.`,
        };
      }
    }
  }


  return {
    valid: true,
    message: '',
  };
};