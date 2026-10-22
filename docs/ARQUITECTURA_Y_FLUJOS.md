# Arquitectura y flujos del Portal Infraestructura TI

Este documento describe el comportamiento implementado. Los diagramas se
entregan en PNG para lectura directa, SVG para ampliar sin pérdida y Mermaid
para modificarlos en el futuro.

Para revisar qué puede hacer cada rol dentro de cada módulo, consultar el
[mapa de acciones actuales](ACCIONES_ACTUALES.md).

## 1. Flujo general

[Abrir imagen PNG](diagramas/flujo_sistema_general.png) ·
[Abrir imagen SVG](diagramas/flujo_sistema_general.svg) ·
[Editar fuente Mermaid](diagramas/fuentes/flujo_sistema_general.mmd)

![Flujo general del portal](diagramas/flujo_sistema_general.png)

El recorrido normal de una operación es:

1. React presenta la vista y envía la solicitud mediante el cliente Axios
   común.
2. Django valida CSRF cuando corresponde, el access token JWT, el identificador
   `sid` y la vigencia de `PortalSession`.
3. `PortalRolePermission` comprueba el rol y la acción solicitada.
4. El serializer y el servicio de dominio validan la operación.
5. Las asignaciones críticas se ejecutan dentro de `transaction.atomic()` y
   bloquean los registros necesarios con `select_for_update()`.
6. La base aplica también claves foráneas, valores únicos y restricciones
   `CHECK`.
7. El cambio funcional queda en su historial. Las operaciones sensibles, como
   revelar una contraseña, generan además un `SecurityAuditLog`.

Tras confirmar una escritura REST, Channels emite un aviso mínimo con el módulo
afectado. Cada navegador conectado por `/ws/changes/` vuelve a consultar solo
los datos visibles que necesita. Daphne sirve HTTP y WebSocket; en DEV se usa
una capa de canales en memoria y en producción se requiere Redis privado para
compartir los avisos entre procesos. El cliente reconecta con espera progresiva
si se interrumpe la conexión.

Cada registro editable y archivable incluye una versión incremental. El
frontend envía la versión que tenía al abrir el formulario y el backend bloquea
la fila antes de guardar. Si otra sesión o una relación interna ya modificó el
registro, la API responde `409 Conflict`, descarta el formulario desactualizado
y solicita nuevamente los datos. Así, el aviso WebSocket actualiza las vistas y
la versión evita que un formulario antiguo sobrescriba el cambio más reciente.

### Autenticación y sesión

- El access token JWT vive en memoria del frontend.
- El refresh token se guarda en una cookie `HttpOnly`; JavaScript no puede
  leerlo.
- Cada inicio válido crea un `sid` único asociado a una `PortalSession`.
- El backend valida la actividad real y permite revocar una sesión concreta.
- El tiempo de inactividad predeterminado es 300 segundos. Recargar la página
  no cierra una sesión todavía vigente porque el frontend renueva el access
  token usando la cookie.
- Los refresh tokens rotan y los reemplazados pasan a la lista de bloqueo.
- Cambiar la contraseña, desactivar la cuenta, cambiar `is_superuser` o
  modificar sus grupos revoca todas sus sesiones y refresh tokens.
- El login se limita por IP y por nombre de usuario. Login administrativo,
  refresh, revelado de secretos, API general y operaciones pesadas tienen
  ámbitos independientes.
- Producción usa Redis como caché compartida para que los límites sean iguales
  en todos los procesos. Los rechazos `429` quedan en `SecurityAuditLog`.
- El WebSocket limita conexiones por IP y usuario, limita mensajes y se cierra
  al vencer o revocar la sesión. El mensaje inicial admite únicamente `type`
  y `token`, y todo mensaje tiene un máximo predeterminado de 16 KiB.

| Ámbito | Tasa predeterminada | Clave |
| --- | --- | --- |
| Login del portal | 10/min | IP |
| Login del portal | 5/15min | Usuario escrito |
| Login de Django Admin | 10/min y 5/15min | IP y usuario escrito |
| Refresh | 10/min | IP |
| Revelado de secretos | 5/min | Usuario autenticado |
| Operaciones pesadas | 20/hour | Usuario autenticado |
| API general | 1200/hour | Usuario autenticado |
| API anónima | 60/hour | IP |
| WebSocket conectado | 20 conexiones | IP |
| WebSocket conectado | 5 conexiones | Usuario autenticado |
| Mensajes WebSocket | 5/segundo | IP y usuario autenticado |
| Tamaño de mensaje WebSocket | 16 KiB | Conexión |

### Roles

| Rol | Alcance |
| --- | --- |
| Visualizador | Vista completa sin sidebar para lectura y búsqueda de Anexos asignados; no muestra observaciones ni acciones. |
| Operador Infraestructura | Lectura, creación, edición y asignación; no elimina ni revela secretos. |
| Administrador | Acceso completo y revelado de secretos después de reautenticarse. |
| Superusuario | Se trata como Administrador. |

## 2. Estados del usuario y recursos

[Abrir imagen PNG](diagramas/flujo_estados_usuario.png) ·
[Abrir imagen SVG](diagramas/flujo_estados_usuario.svg) ·
[Editar fuente Mermaid](diagramas/fuentes/flujo_estados_usuario.mmd)

![Flujo de estados del usuario](diagramas/flujo_estados_usuario.png)

Antes de guardar un cambio de estado, la interfaz explica sus consecuencias.
El backend vuelve a validar la operación y aplica todos sus efectos en una
transacción.

| Estado final | IP | Equipos | Anexo |
| --- | --- | --- | --- |
| `ACTIVO` | Puede mantener o recibir una IP. | Se mantienen; se pueden asignar. | Se mantiene; se puede asignar. |
| `LICENCIA` | Se libera. | Se mantienen asignados. | Se mantiene asignado. |
| `BAJA` | Se libera. | Se desasignan. | Se libera. |

Las liberaciones y asignaciones originadas en otros módulos se relacionan
también con el historial del usuario mediante `modulo_relacionado` y
`objeto_relacionado_id`. Así se puede reconstruir el movimiento desde la ficha
del usuario y desde el recurso afectado.

### Acta de entrega

El acta solo se puede emitir si existe al menos un equipo actualmente asignado
al usuario. La interfaz deshabilita la acción y explica el motivo; el endpoint
vuelve a comprobarlo y responde `409 Conflict` si alguien intenta omitir la
interfaz. Cuando la relación existe, el backend genera el PDF con los datos y
equipos vigentes. Todo dato persistido se escapa como texto antes de entregarlo
a ReportLab; ninguna etiqueta ingresada en nombres, áreas o equipos puede
provocar lecturas de archivos ni conexiones salientes.

### Importaciones XLSX

Los comandos históricos aceptan exclusivamente libros `.xlsx` locales y
regulares. Antes de abrirlos validan firma ZIP, enlaces simbólicos, rutas
internas, cantidad de miembros, tamaño comprimido y descomprimido, filas y
columnas. Las fórmulas se leen mediante su valor almacenado y la aplicación
continúa siendo transaccional.

## 3. Sincronización de IP

`AsignacionIP` representa al propietario formal y exclusivo de cada dirección.
Los campos directos presentes en `IP`, `Usuario`, `Servidor` y `PCGenerico` se
mantienen como proyecciones compatibles para las vistas existentes.

El servicio de asignación:

1. bloquea la IP y los propietarios involucrados;
2. comprueba que la dirección siga libre y pertenezca al segmento permitido;
3. reemplaza o libera la asignación anterior;
4. sincroniza las proyecciones directas;
5. registra `HistorialAsignacionIP` y el historial relacionado del usuario;
6. confirma todo junto o revierte todo ante un fallo.

Una IP puede tener exactamente uno de estos propietarios: usuario, servidor,
PC genérico u otro dispositivo/servicio descrito en texto.

## 4. Archivos reproducibles

- `diagramas/fuentes/generar_diagramas.py` genera los PNG y SVG sin consultar
  la base de datos.
- Los archivos `.mmd` contienen una versión editable en Mermaid.
- Para regenerar las imágenes:

```powershell
.\venv\Scripts\python.exe docs\diagramas\fuentes\generar_diagramas.py
```

El modelo físico y sus restricciones se documentan en
[MODELO_DATOS.md](MODELO_DATOS.md).
