/* =========================
   NORMALIZACIÓN DE TIPOS
========================= */

const normalizeEquipmentType = (tipo = '') =>
  tipo.trim().toLowerCase();


/* =========================
   TIPOS DE EQUIPO
========================= */

const HOSTNAME_TYPES = [
  'notebook',
  'mac',
];

const MOBILE_LINE_TYPES = [
  'celular',
  'tablet',
  'bam / router',
];

const PERIPHERAL_TYPES = [
  'monitor',
  'adaptador',
  'audífonos',
  'teclado',
  'mouse',
  'docking',
  'otro periférico',
];


/* =========================
   REGLAS GENERALES
========================= */

/*
  Solo Notebook y Mac utilizan Hostname.
*/
export const equipmentUsesHostname = (tipo) => {
  return HOSTNAME_TYPES.includes(
    normalizeEquipmentType(tipo)
  );
};


/*
  Equipos que pueden utilizar SIM /
  número de teléfono.
*/
export const equipmentUsesMobileLine = (tipo) => {
  return MOBILE_LINE_TYPES.includes(
    normalizeEquipmentType(tipo)
  );
};


/*
  Identificar periféricos.
*/
export const equipmentIsPeripheral = (tipo) => {
  return PERIPHERAL_TYPES.includes(
    normalizeEquipmentType(tipo)
  );
};


/* =========================
   CAMBIO DE TIPO
========================= */

/*
  Al cambiar el tipo de equipo,
  limpia automáticamente campos
  que ya no corresponden.

  Ejemplo:

  Notebook -> Celular
  elimina hostname.

  Celular -> Notebook
  elimina numero_telefono.
*/
export const normalizeEquipmentFieldsByType = (
  currentState,
  newType
) => {
  const nextState = {
    ...currentState,
    tipo: newType,
  };

  if (!equipmentUsesHostname(newType)) {
    nextState.hostname = '';
  }

  if (!equipmentUsesMobileLine(newType)) {
    nextState.numero_telefono = '';
  }

  return nextState;
};


/* =========================
   IDENTIFICADOR PARA TABLA
========================= */

/*
  Determina qué mostrar en la columna
  "Identificador" de Equipos.
*/
export const getEquipmentIdentifier = (
  equipo = {}
) => {
  if (equipmentUsesHostname(equipo.tipo)) {
    return equipo.hostname || null;
  }

  if (equipmentUsesMobileLine(equipo.tipo)) {
    return equipo.numero_telefono || null;
  }

  return null;
};


/*
  Permite usar el nombre correcto
  dentro de formularios o detalles.
*/
export const getEquipmentIdentifierLabel = (
  tipo
) => {
  if (equipmentUsesHostname(tipo)) {
    return 'Hostname';
  }

  if (equipmentUsesMobileLine(tipo)) {
    return 'SIM / N° Celular';
  }

  return null;
};


/* =========================
   ASIGNACIÓN POR HOSTNAME
========================= */

export const buildEquipmentStateFromHostname = (
  hostnameValue,
  currentState,
  usuariosList = []
) => {
  /*
    Por seguridad, solo buscamos usuario
    por hostname cuando el tipo realmente
    utiliza hostname.
  */
  if (
    currentState.tipo &&
    !equipmentUsesHostname(currentState.tipo)
  ) {
    return {
      ...currentState,
      hostname: '',
    };
  }

  const normalizedHostname = hostnameValue
    .trim()
    .toLowerCase();

  const matchingUser = usuariosList.find(
    (usuario) =>
      usuario.hostname &&
      usuario.hostname
        .trim()
        .toLowerCase() === normalizedHostname
  );

  if (matchingUser) {
    return {
      ...currentState,
      hostname: hostnameValue,
      usuario: matchingUser.id,
      estado: 'ASIGNADO',
    };
  }

  return {
    ...currentState,
    hostname: hostnameValue,
  };
};


/* =========================
   FILTRO POR CATEGORÍA
========================= */

export const filterEquiposByCategory = (
  data = [],
  selectedCategory,
  formatEquipmentType
) => {
  if (!selectedCategory) {
    return data;
  }

  // Categoría agrupadora de periféricos
  if (selectedCategory === 'PERIFERICOS') {
    return data.filter((item) => {
      const itemType = formatEquipmentType(
        item.tipo
      ).toLowerCase();

      return PERIPHERAL_TYPES.includes(
        itemType
      );
    });
  }

  // Categorías normales
  const selectedType = formatEquipmentType(
    selectedCategory
  ).toLowerCase();

  return data.filter((item) => {
    const itemType = formatEquipmentType(
      item.tipo
    ).toLowerCase();

    return itemType === selectedType;
  });
};