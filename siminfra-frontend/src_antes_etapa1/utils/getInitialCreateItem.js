export const getInitialCreateItem = (
  tab,
  dptosList = []
) => {
  switch (tab) {
    case 'usuarios':
      return {
        estado: 'ACTIVO',
        nombre_completo: '',
        hostname: '',
        cargo: '',
        dpto_area: dptosList[0] || '',
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
        usuario: '',
        fecha_asignacion: '',
        numero_telefono: '',
        imei: '',
        pin: '',
        icloud_cuenta: '',
        icloud_password: '',
        estado: 'ASIGNADO',
      };

    case 'perfiles':
      return {
        nombre: '',
        usuario: '',
        password: '',
        correo: '',
        dpto_area: dptosList[0] || '',
        tipo: 'On Premise',
        estado: 'ACTIVO',
      };

    case 'ips':
      return {
        direccion_ip: '',
        estado: 'LIBRE',
        observacion: '',
        usuario: '',
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
        dpto_area: dptosList[0] || '',
        marca: '',
        modelo: '',
        numero_serie: '',
        activo_fijo: '',
        observaciones: '',
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