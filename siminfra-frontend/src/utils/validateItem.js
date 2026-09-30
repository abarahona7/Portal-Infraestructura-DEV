import { isManagedIpAddress } from './ipHelpers';

const normalize = (value = '') => String(value ?? '').trim();
const normalizeLower = (value = '') => normalize(value).toLowerCase();

const isValidIPv4 = (value = '') => {
  const parts = normalize(value).split('.');
  if (parts.length !== 4) return false;

  return parts.every((part) => {
    if (!/^\d+$/.test(part)) return false;
    const number = Number(part);
    return number >= 0 && number <= 255;
  });
};

const isValidEmail = (value = '') => {
  const email = normalize(value);
  if (!email) return true;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

const isValidHostname = (value = '') => {
  const hostname = normalize(value);
  if (!hostname) return true;
  return /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(hostname);
};

const hasWhitespace = (value = '') => /\s/.test(normalize(value));

export const validateItem = (tab, item, data = []) => {
  /* ========================= IPS ========================= */
  if (tab === 'ips') {
    const direccionIp = normalize(item.direccion_ip);
    const asignadoOtro = normalize(item.asignado_otro);
    const observacion = normalize(item.observacion);

    if (!isValidIPv4(direccionIp)) {
      return { valid: false, message: 'Por favor ingrese una dirección IP válida (ejemplo: 172.23.1.50).' };
    }
    if (!isManagedIpAddress(direccionIp)) {
      return { valid: false, message: 'La IP debe pertenecer a uno de los segmentos visibles en Gestión IPs y usar un host entre 1 y 254.' };
    }
    if (data.some((ip) => ip.id !== item.id && normalize(ip.direccion_ip) === direccionIp)) {
      return { valid: false, message: `Error: La dirección IP "${direccionIp}" ya existe en el sistema.` };
    }
    if (asignadoOtro.length > 150) {
      return { valid: false, message: 'El campo "Asignado a otro" puede tener como máximo 150 caracteres.' };
    }
    if (observacion.length > 255) {
      return { valid: false, message: 'La observación puede tener como máximo 255 caracteres.' };
    }
    if (item.usuario && asignadoOtro) {
      return { valid: false, message: 'Esta IP ya pertenece a un usuario. La asignación debe gestionarse desde Usuarios.' };
    }
  }

  /* ========================= SERVIDORES ========================= */
  if (tab === 'servidores') {
    const ip = normalize(item.ip);
    const hostname = normalize(item.hostname);

    if (!ip) return { valid: false, message: 'Debe seleccionar la dirección IP del servidor.' };
    if (!isValidIPv4(ip) || !ip.startsWith('172.23.1.')) {
      return { valid: false, message: 'Seleccione una IP disponible del segmento 172.23.1.0/24.' };
    }
    if (data.some((servidor) => servidor.id !== item.id && normalize(servidor.ip) === ip)) {
      return { valid: false, message: `Error: La IP "${ip}" ya está registrada en otro servidor.` };
    }
    if (!hostname) return { valid: false, message: 'Debe ingresar el Hostname del servidor.' };
    if (hostname.length > 100) return { valid: false, message: 'El Hostname puede tener como máximo 100 caracteres.' };
    if (!isValidHostname(hostname)) {
      return { valid: false, message: 'El Hostname solo puede contener letras, números, punto, guion y guion bajo, sin espacios.' };
    }
    if (data.some((servidor) => servidor.id !== item.id && normalizeLower(servidor.hostname) === hostname.toLowerCase())) {
      return { valid: false, message: `Error: El Hostname "${hostname}" ya está registrado en otro servidor.` };
    }
  }

  /* ========================= ANEXOS ========================= */
  if (tab === 'anexos') {
    const numeroAnexo = normalize(item.numero_anexo);
    const exterior = normalize(item.exterior);

    if (!numeroAnexo) return { valid: false, message: 'Debe ingresar un número de anexo.' };
    if (!/^\d+$/.test(numeroAnexo)) return { valid: false, message: 'El número de anexo debe contener solo números.' };
    if (numeroAnexo.length > 10) return { valid: false, message: 'El número de anexo puede tener como máximo 10 dígitos.' };
    if (data.some((anexo) => anexo.id !== item.id && normalize(anexo.numero_anexo) === numeroAnexo)) {
      return { valid: false, message: `Error: El anexo "${numeroAnexo}" ya existe en el sistema.` };
    }
    if (exterior && !/^\+\d{11}$/.test(exterior)) {
      return { valid: false, message: 'El número exterior debe comenzar con + y contener exactamente 11 números. Ejemplo: +56254698789.' };
    }
    if (item.usuario) {
      const duplicate = data.find((anexo) => anexo.id !== item.id && Number(anexo.usuario) === Number(item.usuario));
      if (duplicate) {
        return { valid: false, message: `Error: Este usuario ya tiene asignado el anexo "${duplicate.numero_anexo}".` };
      }
    }
  }

  /* ========================= PERFILES GENÉRICOS ========================= */
  if (tab === 'perfiles') {
    const nombre = normalize(item.nombre);
    const usuario = normalize(item.usuario);
    const correo = normalize(item.correo);

    if (!nombre) return { valid: false, message: 'Debe ingresar el Nombre / Perfil.' };
    if (nombre.length > 150) return { valid: false, message: 'El Nombre / Perfil puede tener como máximo 150 caracteres.' };
    if (!usuario) return { valid: false, message: 'Debe ingresar el Usuario del Perfil Genérico.' };
    if (usuario.length > 100) return { valid: false, message: 'El Usuario del Perfil puede tener como máximo 100 caracteres.' };
    if (hasWhitespace(usuario)) return { valid: false, message: 'El Usuario del Perfil Genérico no puede contener espacios.' };
    if (!item.departamento) return { valid: false, message: 'Debe seleccionar un Departamento.' };
    if (correo && !isValidEmail(correo)) return { valid: false, message: 'Ingrese un correo válido para el Perfil Genérico.' };
    if (item.tipo && !['On Premise', 'O365'].includes(item.tipo)) {
      return { valid: false, message: 'El Tipo de Cuenta seleccionado no es válido.' };
    }
    if (data.some((perfil) => perfil.id !== item.id && normalizeLower(perfil.usuario) === usuario.toLowerCase())) {
      return { valid: false, message: `Error: El usuario de Perfil Genérico "${usuario}" ya existe.` };
    }
  }

  /* ========================= PCS GENÉRICOS ========================= */
  if (tab === 'pcs-genericos') {
    const usuarioLocal = normalize(item.usuario_local);
    const hostname = normalize(item.hostname);
    const numeroSerie = normalize(item.numero_serie);
    const activoFijo = normalize(item.activo_fijo);
    const teamviewerId = normalize(item.teamviewer_id);

    if (!usuarioLocal) return { valid: false, message: 'Debe ingresar el Usuario Local del PC Genérico.' };
    if (usuarioLocal.length > 150) return { valid: false, message: 'El Usuario Local puede tener como máximo 150 caracteres.' };
    if (!hostname) return { valid: false, message: 'Debe ingresar el Hostname del PC Genérico.' };
    if (hostname.length > 100) return { valid: false, message: 'El Hostname puede tener como máximo 100 caracteres.' };
    if (!isValidHostname(hostname)) return { valid: false, message: 'El Hostname solo puede contener letras, números, punto, guion y guion bajo, sin espacios.' };
    if (!item.departamento) return { valid: false, message: 'Debe seleccionar un Departamento.' };
    if (data.some((pc) => pc.id !== item.id && normalizeLower(pc.hostname) === hostname.toLowerCase())) {
      return { valid: false, message: `Error: El Hostname "${hostname}" ya está registrado en otro PC Genérico.` };
    }
    if (numeroSerie.length > 20) return { valid: false, message: 'El N° de Serie puede tener como máximo 20 caracteres.' };
    if (numeroSerie && data.some((pc) => pc.id !== item.id && normalizeLower(pc.numero_serie) === numeroSerie.toLowerCase())) {
      return { valid: false, message: `Error: El N° de Serie "${numeroSerie}" ya está registrado en otro PC Genérico.` };
    }
    if (activoFijo.length > 12) return { valid: false, message: 'El Activo Fijo puede tener como máximo 12 caracteres.' };
    if (activoFijo && !/^[A-Za-z0-9]+$/.test(activoFijo)) return { valid: false, message: 'El Activo Fijo solo puede contener letras y números.' };
    if (activoFijo && data.some((pc) => pc.id !== item.id && normalizeLower(pc.activo_fijo) === activoFijo.toLowerCase())) {
      return { valid: false, message: `Error: El Activo Fijo "${activoFijo}" ya está registrado en otro PC Genérico.` };
    }
    if (teamviewerId.length > 20) return { valid: false, message: 'El ID TeamViewer puede tener como máximo 20 caracteres.' };
    if (normalize(item.marca).length > 100 || normalize(item.modelo).length > 100) {
      return { valid: false, message: 'Marca y Modelo pueden tener como máximo 100 caracteres.' };
    }
  }

  /* ========================= USUARIOS ========================= */
  if (tab === 'usuarios') {
    const nombre = normalize(item.nombre_completo);
    const usuarioRed = normalize(item.usuario_red);
    const correo = normalize(item.correo_corp);
    const gmail = normalize(item.gmail);
    const hostname = normalize(item.hostname);
    const cargo = normalize(item.cargo);

    if (!nombre) return { valid: false, message: 'Debe ingresar el Nombre Completo.' };
    if (nombre.length > 150) return { valid: false, message: 'El Nombre Completo puede tener como máximo 150 caracteres.' };
    if (!item.departamento) return { valid: false, message: 'Debe seleccionar un Departamento.' };
    if (cargo.length > 100) return { valid: false, message: 'El Cargo puede tener como máximo 100 caracteres.' };
    if (!usuarioRed) return { valid: false, message: 'Debe ingresar el Usuario de Red.' };
    if (usuarioRed.length > 50) return { valid: false, message: 'El Usuario de Red puede tener como máximo 50 caracteres.' };
    if (hasWhitespace(usuarioRed)) return { valid: false, message: 'El Usuario de Red no puede contener espacios.' };
    if (!correo) return { valid: false, message: 'Debe ingresar el Correo Corporativo.' };
    if (!isValidEmail(correo)) return { valid: false, message: 'Ingrese un Correo Corporativo válido.' };
    if (gmail && !isValidEmail(gmail)) return { valid: false, message: 'Ingrese un correo Gmail válido.' };
    if (hostname.length > 50) return { valid: false, message: 'El Hostname puede tener como máximo 50 caracteres.' };
    if (hostname && !isValidHostname(hostname)) return { valid: false, message: 'El Hostname solo puede contener letras, números, punto, guion y guion bajo, sin espacios.' };

    if (data.some((usuario) => usuario.id !== item.id && normalizeLower(usuario.nombre_completo) === nombre.toLowerCase())) {
      return { valid: false, message: `Error: Ya existe un usuario llamado "${nombre}".` };
    }
    if (data.some((usuario) => usuario.id !== item.id && normalizeLower(usuario.usuario_red) === usuarioRed.toLowerCase())) {
      return { valid: false, message: `Error: El usuario de red "${usuarioRed}" ya existe.` };
    }
    if (data.some((usuario) => usuario.id !== item.id && normalizeLower(usuario.correo_corp) === correo.toLowerCase())) {
      return { valid: false, message: `Error: El correo corporativo "${correo}" ya está registrado.` };
    }
    if (hostname && data.some((usuario) => usuario.id !== item.id && normalizeLower(usuario.hostname) === hostname.toLowerCase())) {
      return { valid: false, message: `Error: El Hostname "${hostname}" ya está registrado en otro usuario.` };
    }
  }

  /* ========================= EQUIPOS ========================= */
  if (tab === 'equipos') {
    const marca = normalize(item.marca);
    const modelo = normalize(item.modelo);
    const numeroSerie = normalize(item.numero_serie);
    const af = normalize(item.af);
    const telefono = normalize(item.numero_telefono);
    const hostname = normalize(item.hostname);
    const original = item.id ? data.find((equipo) => equipo.id === item.id) : null;
    const exigeFichaTecnica = !item.id || (original && original.tipo !== item.tipo);

    if (exigeFichaTecnica && item.tipo === 'Celular' && !normalize(item.imei)) {
      return { valid: false, message: 'Indique el IMEI del celular.' };
    }
    if (exigeFichaTecnica && ['Notebook', 'Mac'].includes(item.tipo)) {
      if (!hostname) return { valid: false, message: 'Indique el Hostname del equipo.' };
      if (!normalize(item.mac_address)) return { valid: false, message: 'Indique la MAC Address del equipo.' };
    }

    if (!marca) return { valid: false, message: 'Debe ingresar la Marca del equipo.' };
    if (marca.length > 50) return { valid: false, message: 'La Marca puede tener como máximo 50 caracteres.' };
    if (!modelo) return { valid: false, message: 'Debe ingresar el Modelo del equipo.' };
    if (modelo.length > 50) return { valid: false, message: 'El Modelo puede tener como máximo 50 caracteres.' };
    if (numeroSerie.length > 20) return { valid: false, message: 'El N° de Serie puede tener como máximo 20 caracteres.' };
    if (numeroSerie && data.some((equipo) => equipo.id !== item.id && normalizeLower(equipo.numero_serie) === numeroSerie.toLowerCase())) {
      return { valid: false, message: `Error: El número de serie "${numeroSerie}" ya está registrado.` };
    }
    if (af.length > 12) return { valid: false, message: 'El Activo Fijo (AF) puede tener máximo 12 caracteres.' };
    if (af && !/^[A-Za-z0-9]+$/.test(af)) return { valid: false, message: 'El Activo Fijo (AF) solo puede contener letras y números.' };
    if (af && data.some((equipo) => equipo.id !== item.id && normalizeLower(equipo.af) === af.toLowerCase())) {
      return { valid: false, message: `Error: El Activo Fijo (AF) "${af}" ya pertenece a otro equipo.` };
    }
    if (telefono && !/^\+\d{11}$/.test(telefono)) {
      return { valid: false, message: 'El número telefónico debe comenzar con + y contener exactamente 11 números. Ejemplo: +56912345678.' };
    }
    if (hostname.length > 50) return { valid: false, message: 'El Hostname puede tener como máximo 50 caracteres.' };
    if (hostname && !isValidHostname(hostname)) return { valid: false, message: 'El Hostname solo puede contener letras, números, punto, guion y guion bajo, sin espacios.' };
  }

  return { valid: true, message: '' };
};
