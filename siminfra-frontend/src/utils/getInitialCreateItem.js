export const getInitialCreateItem = (tab) => {
  switch (tab) {
    case 'usuarios':
      return {
        estado: 'ACTIVO',
        nombre_completo: '',
        hostname: '',
        cargo: '',
        rut: '',
        centro_costo: '',
        ubicacion: 'Casa Matriz - Quilicura',
        dpto_area: '',
        departamento: null,
        subarea: null,
        usuario_red: '',
        correo_corp: '',
        gmail: '',
        password_gmail: '',
        password_vpn: '',
        ip_seleccionada: null,
      };

    case 'equipos':
      return {
        tipo: 'Notebook',
        marca: '',
        modelo: '',
        numero_serie: '',
        hostname: '',
        af: '',
        numero_telefono: '',
        imei: '',
        pin: '',
        icloud_cuenta: '',
        icloud_password: '',
        estado: 'STOCK',
        estado_fisico: 'USADO',
        ubicacion_actual: 'Bodega TI',
        mac_address: '',
      };

    case 'perfiles':
      return {
        nombre: '',
        usuario: '',
        password: '',
        correo: '',
        dpto_area: '',
        departamento: null,
        subarea: null,
        tipo: 'On Premise',
        estado: 'ACTIVO',
        observaciones: '',
      };

    case 'ips':
      return {
        direccion_ip: '',
        observacion: '',
        asignado_otro: '',
      };

    case 'anexos':
      return {
        numero_anexo: '',
        exterior: '',
        usuario: '',
        observaciones: '',
      };

    case 'pcs-genericos':
      return {
        usuario_local: '',
        password: '',
        hostname: '',
        dpto_area: '',
        departamento: null,
        subarea: null,
        marca: '',
        modelo: '',
        numero_serie: '',
        activo_fijo: '',
        observaciones: '',
        ip_seleccionada: null,
      };

    case 'servidores':
      return {
        ip: '',
        hostname: '',
        descripcion: '',
      };

    default:
      return null;
  }
};
