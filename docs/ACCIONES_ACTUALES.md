# Acciones actuales del Portal Infraestructura TI

Este documento resume las acciones implementadas en la interfaz y las reglas
que el backend vuelve a validar. Las diferencias detectadas para QA están en
[la revisión de ambigüedades](REVISION_AMBIGUEDADES_PRODUCCION.md).

## Diagrama histórico (29-09-2026)

Estas imágenes y su fuente son anteriores a la reconstrucción del Tablero de
activos y la Ficha QR. No deben utilizarse como mapa completo de permisos ni
como documentación gráfica definitiva hasta regenerarlas. Las acciones
vigentes se describen en el texto siguiente.

[Abrir imagen PNG](diagramas/mapa_acciones_actuales.png) ·
[Abrir PNG de alta resolución](diagramas/mapa_acciones_actuales_alta_resolucion.png) ·
[Abrir imagen SVG](diagramas/mapa_acciones_actuales.svg) ·
[Editar fuente Mermaid](diagramas/fuentes/mapa_acciones_actuales.mmd)

## Acciones según el rol

| Rol | Consulta | Crear/editar/asignar | Exportar | Eliminar | Revelar secretos |
| --- | --- | --- | --- | --- | --- |
| Visualizador | Solo Anexos: listado, búsqueda, filtros, paginación e historial | No | No | No | No |
| Operador Infraestructura | Usuarios, Departamentos/Áreas, Equipos, Tablero de activos, Ficha QR, PCs genéricos, Gestión de IP, Servidores, Anexos y Perfiles genéricos | Donde existe la acción; Tablero y QR son de consulta | Donde existe la exportación | No | No |
| Administrador | Todos los módulos | Sí | Sí | Sí, según las reglas del módulo | Sí, tras reautenticación |
| Superusuario | Igual que Administrador | Sí | Sí | Sí, según las reglas del módulo | Sí, tras reautenticación |

La autorización se comprueba en el backend. Ocultar un botón en la interfaz
mejora la experiencia, pero no es el control de seguridad definitivo.

## Acciones por módulo

### Usuarios

- Seleccionar un departamento o área y consultar sus usuarios, o buscar por
  nombre y otros datos en todas las áreas.
- Buscar con actualización diferida breve, paginar y exportar el resultado.
- Agregar, editar, eliminar con permiso administrativo y abrir la ficha.
- Elegir primero el segmento de red y luego una IP disponible.
- Consultar IP, hostname, teléfono, anexo, equipos y credenciales asociados.
- Asignar equipos y anexo mediante sus módulos relacionados.
- Consultar el historial propio y los movimientos originados en otros módulos.
- Revelar las claves de Gmail o VPN como administrador, previa reautenticación.
- Generar el acta de entrega cuando existe al menos un equipo asignado. Si no
  existe esa relación, la interfaz lo explica y el backend responde `409`.
- Cambiar el estado con una advertencia previa: `LICENCIA` libera solamente la
  IP; `BAJA` libera la IP, desasigna equipos y libera el anexo.
- Al reactivar un usuario desde `BAJA`, la IP y el anexo no se restauran. Un
  Notebook o Mac en stock puede volver a asociarse si su hostname coincide con
  el del usuario; los demás equipos no se restauran desde el historial. Este
  comportamiento requiere validación funcional en QA.

### Equipos

- Pulsar Equipos en el menú lateral para abrir el Tablero de activos: consultar estado general,
  departamentos con más equipos asignados y pendientes; desde estos últimos
  se puede ir al detalle de los equipos afectados.
- Entrar directamente a Notebook, Celular, Tablet, Mac, BAM / Router o
  Periféricos desde el menú lateral.
- Buscar, filtrar por estado, paginar y exportar. Al crear un equipo desde una
  categoría, el tipo queda fijado; en Periféricos solo se ofrecen tipos de
  periférico. El backend valida la misma relación al guardar.
- Agregar, editar, eliminar con permiso administrativo y consultar historial.
- Asignar o desasignar un usuario.
- Ver en Notebook la IP que pertenece al usuario asignado.
- Revelar PIN u otro secreto admitido como administrador, previa
  reautenticación.
- Pulsar un equipo del listado o de los pendientes para abrir su ficha. Los QR
  históricos siguen abriendo esa ficha mediante `/qr/a/<uuid>`, con sesión y
  rol Operador o Administrador. El Visualizador no tiene acceso a estas vistas.

### Gestión de IP

- Seleccionar un segmento y consultar sus direcciones libres o reservadas, o
  buscar una dirección en todos los segmentos.
- Ordenar las direcciones por su último octeto numérico.
- Buscar, filtrar, paginar y exportar.
- Agregar, editar y consultar el historial de asignación.
- Mantener un único propietario: usuario, servidor, PC genérico u otro uso.
- Sincronizar automáticamente la dirección, el propietario y el estado.
- Liberar una IP desde el módulo que posee la asignación.
- Eliminar como administrador cuando no existe un vínculo activo con usuario,
  servidor, PC genérico u otra asignación activa. El endpoint aún no verifica
  explícitamente `estado=LIBRE` si el estado quedó desincronizado; esta brecha
  está registrada para corregirla antes de producción.

### Anexos

- Listar, buscar, filtrar, paginar y exportar.
- Agregar, editar y eliminar con permiso administrativo.
- Asignar o liberar un usuario y mantener coherentes dueño y estado.
- Consultar el historial de movimientos.
- Permitir al Visualizador únicamente las acciones de consulta e historial.

### Perfiles genéricos

- Filtrar por departamento o subárea, buscar, paginar y exportar.
- Agregar, editar, activar, desactivar y consultar historial.
- Eliminar con permiso administrativo.
- Revelar la contraseña como administrador, previa reautenticación.

### Departamentos y subáreas

- Buscar y recorrer las tarjetas en orden.
- Agregar, editar, activar o desactivar departamentos.
- Agregar una subárea cuando el departamento está activo.
- Editar, activar o desactivar subáreas sin perder las relaciones existentes.
- Eliminar como administrador solo cuando no existen usuarios, perfiles, PCs
  genéricos ni subáreas relacionados, según el tipo de registro.

### PCs genéricos

- Buscar, filtrar por departamento, paginar y exportar.
- Agregar, editar y relacionar departamento o subárea.
- Elegir un segmento y luego una IP disponible.
- Mostrar la IP asignada y sincronizar sus cambios con Gestión de IP.
- Consultar historial, revelar contraseña como administrador y eliminar con
  permiso administrativo.

### Servidores

- Buscar, paginar y exportar.
- Agregar y editar seleccionando una IP disponible de `172.23.1.0/24`.
- Cambiar la IP y sincronizar su estado en Gestión de IP. La API exige una IP
  al crear o editar; eliminar el servidor libera su IP.
- Consultar historial y eliminar con permiso administrativo.

## Flujo común al confirmar

1. El backend valida la sesión, el rol, los campos, los duplicados y las
   relaciones requeridas.
2. Las operaciones relacionadas se aplican dentro de una transacción para que
   se confirmen juntas o se reviertan ante un fallo.
3. Las asignaciones actualizan el recurso, su propietario y su estado.
4. El historial registra actor, fecha, acción, valores anteriores y valores
   nuevos. Los eventos sensibles se registran además en la auditoría de
   seguridad.
5. La interfaz informa el resultado y actualiza los registros afectados.

Texto contrastado con la implementación del repositorio al 05-10-2026. El
diagrama histórico conserva su fecha original hasta su actualización.
