import { exportToExcel } from './excelExport';
import { formatEquipmentType } from './formatEquipmentType';
import { getIpSegment } from './ipHelpers';


/* =========================
   USUARIOS
========================= */

export const exportUsuariosExcel = ({
  rows,
  selectedDpto,
}) => {
  return exportToExcel({
    rows,

    fileName: selectedDpto
      ? `usuarios_${selectedDpto}`
      : 'usuarios_general',

    sheetName: 'Usuarios',

    columns: [
      {
        key: 'nombre_completo',
        header: 'Nombre Completo',
      },
      {
        key: 'departamento',
        header: 'Departamento',
        value: (usuario) =>
          usuario.departamento_nombre || usuario.dpto_area || 'N/I',
      },
      {
        key: 'subarea',
        header: 'Subárea',
        value: (usuario) =>
          usuario.subarea_nombre || 'N/I',
      },
      {
        key: 'cargo',
        header: 'Cargo',
      },
      {
        key: 'estado',
        header: 'Estado',
      },
      {
        key: 'usuario_red',
        header: 'Usuario Red',
      },
      {
        key: 'hostname',
        header: 'Hostname',
      },
      {
        key: 'correo_corp',
        header: 'Correo Corporativo',
      },

      {
        key: 'ip_actual',
        header: 'IP Asignada',
        value: (usuario) =>
          usuario.ip_actual || 'N/I',
      },
      {
        key: 'numero_anexo',
        header: 'Anexo',
        value: (usuario) =>
          usuario.anexo_actual
            ?.numero_anexo || 'N/I',
      },
      {
        key: 'exterior',
        header: 'Exterior',
        value: (usuario) =>
          usuario.anexo_actual
            ?.exterior || 'N/I',
      },

      {
        key: 'celular_corporativo',
        header: 'Celular Corporativo',
        value: (usuario) => {
          const celulares = (
            usuario.equipos || []
          ).filter((equipo) => {
            const tipo = String(
              equipo.tipo || ''
            )
              .trim()
              .toUpperCase();

            return (
              tipo === 'CEL' ||
              tipo === 'CELULAR'
            );
          });

          const numeros = celulares
            .map(
              (equipo) =>
                equipo.numero_telefono
            )
            .filter(Boolean);

          const numerosUnicos = [
            ...new Set(numeros)
          ];

          return numerosUnicos.length
            ? numerosUnicos.join(' / ')
            : 'N/I';
        },
      },

      {
        key: 'gmail',
        header: 'Cuenta Gmail',
        value: (usuario) =>
          usuario.gmail || 'N/I',
      },
      {
        key: 'vpn_configurada',
        header: 'VPN Cisco',
        value: (usuario) =>
          usuario.password_vpn_configured
            ? 'Configurada'
            : 'No configurada',
      },

      {
        key: 'cantidad_equipos',
        header: 'Cantidad Equipos',
        value: (usuario) =>
          usuario.equipos?.length || 0,
      },
      {
        key: 'equipos_asignados',
        header: 'Equipos Asignados',
        value: (usuario) => {
          const equipos =
            usuario.equipos || [];

          if (equipos.length === 0) {
            return 'Sin equipos asignados';
          }

          return equipos
            .map((equipo) => {
              const datos = [];

              if (equipo.tipo) {
                datos.push(
                  `Tipo: ${formatEquipmentType(
                    equipo.tipo
                  )}`
                );
              }

              const marcaModelo = [
                equipo.marca,
                equipo.modelo,
              ]
                .filter(Boolean)
                .join(' ');

              if (marcaModelo) {
                datos.push(
                  `Equipo: ${marcaModelo}`
                );
              }

              if (equipo.af) {
                datos.push(
                  `AF: ${equipo.af}`
                );
              }

              if (equipo.numero_serie) {
                datos.push(
                  `Serie: ${equipo.numero_serie}`
                );
              }

              if (equipo.hostname) {
                datos.push(
                  `Hostname: ${equipo.hostname}`
                );
              }

              if (equipo.imei) {
                datos.push(
                  `IMEI: ${equipo.imei}`
                );
              }

              if (equipo.numero_telefono) {
                datos.push(
                  `Teléfono: ${equipo.numero_telefono}`
                );
              }

              if (equipo.icloud_cuenta) {
                datos.push(
                  `iCloud: ${equipo.icloud_cuenta}`
                );
              }

              return datos.join(' | ');
            })
            .join(' || ');
        },
      },
    ],
  });
};


/* =========================
   EQUIPOS
========================= */

export const exportEquiposExcel = ({
  rows,
  selectedCategoriaEquipo,
}) => {
  return exportToExcel({
    rows,

    fileName: selectedCategoriaEquipo
      ? `equipos_${selectedCategoriaEquipo}`
      : 'equipos_general',

    sheetName: 'Equipos',

    columns: [
      {
        key: 'tipo',
        header: 'Tipo',
        value: (equipo) =>
          formatEquipmentType(
            equipo.tipo
          ) || 'N/I',
      },
      {
        key: 'marca',
        header: 'Marca',
      },
      {
        key: 'modelo',
        header: 'Modelo',
      },
      {
        key: 'numero_serie',
        header: 'N° Serie',
      },
      {
        key: 'af',
        header: 'Activo Fijo',
      },
      {
        key: 'hostname',
        header: 'Hostname',
        value: (equipo) =>
          equipo.hostname || 'N/I',
      },
      {
        key: 'ip_asignada',
        header: 'IP asignada',
        value: (equipo) =>
          equipo.ip_asignada || 'N/A',
      },
      {
        key: 'numero_telefono',
        header: 'SIM / N° Celular',
        value: (equipo) =>
          equipo.numero_telefono || 'N/I',
      },
      {
        key: 'imei',
        header: 'IMEI',
        value: (equipo) =>
          equipo.imei || 'N/I',
      },
      {
        key: 'icloud_cuenta',
        header: 'Cuenta iCloud',
        value: (equipo) =>
          equipo.icloud_cuenta || 'N/I',
      },
      {
        key: 'accesorios',
        header: 'Accesorios',
        value: (equipo) =>
          equipo.accesorios || 'N/I',
      },
      {
        key: 'usuario_nombre',
        header: 'Asignado a',
        value: (equipo) =>
          equipo.usuario_nombre ||
          'Disponible (Stock)',
      },
      {
        key: 'fecha_asignacion',
        header: 'Fecha Asignación',
        value: (equipo) =>
          equipo.fecha_asignacion || 'N/A',
      },
      {
        key: 'estado',
        header: 'Estado',
        value: (equipo) =>
          equipo.estado ||
          (
            equipo.usuario_nombre
              ? 'ASIGNADO'
              : 'STOCK'
          ),
      },
    ],
  });
};


/* =========================
   IPS
========================= */

export const exportIpsExcel = ({
  rows,
  selectedIpSegment,
}) => {
  return exportToExcel({
    rows,

    fileName: selectedIpSegment
      ? `ips_${selectedIpSegment}`
      : 'ips_general',

    sheetName: 'IPs',

    columns: [
      {
        key: 'direccion_ip',
        header: 'Dirección IP',
      },
      {
        key: 'segmento',
        header: 'Segmento',
        value: (ip) => {
          const segment = getIpSegment(
            ip.direccion_ip
          );

          return segment?.label || 'Sin definir';
        },
      },
      {
        key: 'vlan',
        header: 'VLAN',
        value: (ip) => {
          const segment = getIpSegment(
            ip.direccion_ip
          );

          return segment?.network || 'Sin definir';
        },
      },
      {
        key: 'estado',
        header: 'Estado',
        value: (ip) =>
          ip.estado || 'N/I',
      },
      {
        key: 'tipo_asignacion',
        header: 'Tipo Asignación',
        value: (ip) => {
          const assignmentLabels = {
            USUARIO: 'Usuario',
            SERVIDOR: 'Servidor',
            PC_GENERICO: 'PC Genérico',
            OTRO: 'Otro dispositivo',
          };

          if (ip.tipo_asignacion) {
            return assignmentLabels[ip.tipo_asignacion] || ip.tipo_asignacion;
          }

          if (ip.usuario_nombre) {
            return 'Usuario';
          }

          if (ip.asignado_otro) {
            return 'Otro dispositivo';
          }

          return 'Sin asignar';
        },
      },
      {
        key: 'asignado_a',
        header: 'Asignado a',
        value: (ip) =>
          ip.asignado_a ||
          ip.usuario_nombre ||
          ip.asignado_otro ||
          'Sin asignar',
      },
      {
        key: 'observacion',
        header: 'Observaciones',
        value: (ip) =>
          ip.observacion ||
          'Sin observaciones',
      },
    ],
  });
};
/* =========================
   SERVIDORES
========================= */

export const exportServidoresExcel = ({
  rows,
}) => {
  return exportToExcel({
    rows,

    fileName: 'servidores_general',

    sheetName: 'Servidores',

    columns: [
      {
        key: 'ip',
        header: 'Dirección IP',
        value: (servidor) =>
          servidor.ip || 'N/I',
      },
      {
        key: 'hostname',
        header: 'Hostname',
        value: (servidor) =>
          servidor.hostname || 'N/I',
      },
      {
        key: 'descripcion',
        header: 'Descripción',
        value: (servidor) =>
          servidor.descripcion ||
          'Sin descripción',
      },
    ],
  });
};

/* =========================
   PERFILES GENÉRICOS
========================= */

export const exportPerfilesExcel = ({
  rows,
  selectedDpto,
}) => {
  return exportToExcel({
    rows,

    fileName: selectedDpto
      ? `perfiles_${selectedDpto}`
      : 'perfiles_general',

    sheetName: 'Perfiles',

    columns: [
      {
        key: 'nombre',
        header: 'Nombre / Perfil',
        value: (perfil) =>
          perfil.nombre || 'N/I',
      },
      {
        key: 'usuario',
        header: 'Usuario',
        value: (perfil) =>
          perfil.usuario || 'N/I',
      },
      {
        key: 'password_configurada',
        header: 'Contraseña Configurada',
        value: (perfil) =>
          perfil.password_configured
            ? 'Sí'
            : 'No',
      },
      {
        key: 'tipo',
        header: 'Tipo Cuenta',
        value: (perfil) =>
          perfil.tipo || 'N/I',
      },
      {
        key: 'correo',
        header: 'Correo Asignado',
        value: (perfil) =>
          perfil.correo || 'N/I',
      },
      {
        key: 'departamento',
        header: 'Departamento',
        value: (perfil) =>
          perfil.departamento_nombre || perfil.dpto_area || 'N/I',
      },
      {
        key: 'subarea',
        header: 'Subárea',
        value: (perfil) =>
          perfil.subarea_nombre || 'N/I',
      },
      {
        key: 'estado',
        header: 'Estado',
        value: (perfil) =>
          perfil.estado === 'INACTIVO' ? 'Inactivo' : 'Activo',
      },
      {
        key: 'observaciones',
        header: 'Observaciones',
        value: (perfil) =>
          perfil.observaciones ||
          'Sin observaciones',
      },
    ],
  });
};

/* =========================
   ANEXOS
========================= */

export const exportAnexosExcel = ({
  rows,
}) => {
  return exportToExcel({
    rows,

    fileName: 'anexos_general',

    sheetName: 'Anexos',

    columns: [
      {
        key: 'usuario_nombre',
        header: 'Nombre Completo',
        value: (anexo) =>
          anexo.usuario_nombre ||
          'Sin asignar',
      },
      {
        key: 'departamento',
        header: 'Departamento / Área',
        value: (anexo) =>
          anexo.departamento || 'N/I',
      },
      {
        key: 'cargo',
        header: 'Cargo',
        value: (anexo) =>
          anexo.cargo || 'N/I',
      },
      {
        key: 'numero_anexo',
        header: 'Anexo',
        value: (anexo) =>
          anexo.numero_anexo || 'N/I',
      },
      {
        key: 'exterior',
        header: 'Exterior',
        value: (anexo) =>
          anexo.exterior || 'N/I',
      },
      {
        key: 'correo',
        header: 'Correo',
        value: (anexo) =>
          anexo.correo || 'N/I',
      },
      {
        key: 'estado',
        header: 'Estado',
        value: (anexo) =>
          anexo.estado || 'N/I',
      },
      {
        key: 'observaciones',
        header: 'Observaciones',
        value: (anexo) =>
          anexo.observaciones ||
          'Sin observaciones',
      },
    ],
  });
};

/* =========================
   PCS GENÉRICOS
========================= */

export const exportPCsGenericosExcel = ({
  rows,
  selectedDpto,
}) => {
  return exportToExcel({
    rows,

    fileName: selectedDpto
      ? `pcs_genericos_${selectedDpto}`
      : 'pcs_genericos_general',

    sheetName: 'PCs Genericos',

    columns: [
      {
        key: 'usuario_local',
        header: 'Usuario Local',
        value: (pc) =>
          pc.usuario_local || 'N/I',
      },
      {
        key: 'password_configurada',
        header: 'Contraseña Configurada',
        value: (pc) =>
          pc.password_configured
            ? 'Sí'
            : 'No',
      },
      {
        key: 'hostname',
        header: 'Hostname',
        value: (pc) =>
          pc.hostname || 'N/I',
      },
      {
        key: 'ip_actual',
        header: 'Dirección IP',
        value: (pc) =>
          pc.ip_actual || 'Sin IP asignada',
      },
      {
        key: 'dpto_area',
        header: 'Departamento / Área',
        value: (pc) =>
          pc.dpto_area || 'N/I',
      },
      {
        key: 'marca',
        header: 'Marca',
        value: (pc) =>
          pc.marca || 'N/I',
      },
      {
        key: 'modelo',
        header: 'Modelo',
        value: (pc) =>
          pc.modelo || 'N/I',
      },
      {
        key: 'numero_serie',
        header: 'N° Serie',
        value: (pc) =>
          pc.numero_serie || 'N/I',
      },
      {
        key: 'activo_fijo',
        header: 'Activo Fijo',
        value: (pc) =>
          pc.activo_fijo || 'N/I',
      },
      {
        key: 'teamviewer_id',
        header: 'ID TeamViewer',
        value: (pc) =>
          pc.teamviewer_id || 'N/I',
      },
      {
        key: 'observaciones',
        header: 'Observaciones',
        value: (pc) =>
          pc.observaciones ||
          'Sin observaciones',
      },
    ],
  });
};
