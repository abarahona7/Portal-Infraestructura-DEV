# Modelo de amenazas del Portal de Infraestructura TI

## Alcance y límites de confianza

El modelo cubre React, Django REST Framework, Channels, MySQL, Redis, el proxy
inverso y los comandos técnicos. REST y MySQL son la fuente de verdad. El
WebSocket solo informa qué módulos deben volver a consultarse.

Límites de confianza:

1. navegador a proxy mediante HTTPS/WSS;
2. proxy a Daphne por interfaz local;
3. Django a MySQL y Redis privados;
4. operador técnico a comandos de gestión;
5. respaldo cifrado a almacenamiento separado de las claves.

## Flujos y amenazas STRIDE

| Flujo | Amenazas principales | Controles aplicados | Riesgo residual |
| --- | --- | --- | --- |
| Login y sesión | Suplantación, replay y denegación de servicio | CSRF, límites por IP/usuario, JWT corto, refresh HttpOnly rotado, blacklist y `PortalSession` revocable | La caída de Redis deniega el acceso con `503`; requiere monitoreo operativo. |
| Revelado de secretos | Elevación, divulgación y repudio | Solo Administrador, contraseña actual en cada solicitud, límite estricto, auditoría obligatoria y respuesta `no-store` | Un patrón anómalo requiere alerta del recolector. No existe revelado masivo. |
| Consulta de Anexos | Enumeración y divulgación | Visualizador limitado en backend a Anexos asignados, serializer sin observaciones y solo lectura | La recepción puede consultar todos los Anexos asignados por necesidad operativa. |
| Roles y cuentas | Elevación y manipulación | Gestión administrativa, revocación de sesiones ante cambios y auditoría del cambio | No existe doble aprobación para promover a Administrador. |
| Asignaciones | Manipulación, carreras y repudio | Validación en serializer/servicio, transacciones, bloqueos de fila, restricciones de BD e historial | Deadlocks responden `503`; el cliente debe reintentar manualmente. |
| Importación | Manipulación, traversal y agotamiento | Archivo local regular, XLSX validado, límites, huella, simulación previa y transacción completa | Operación técnica con acceso al servidor. |
| Exportación | Divulgación y agotamiento | Rol del módulo, paginación, límite de 5.000 filas, throttle pesado y auditoría obligatoria | Un usuario autorizado aún puede consultar páginas normales dentro del límite general. |
| WebSocket | Suplantación, divulgación y agotamiento | Origin estricto, JWT/sesión/rol, tamaño, frecuencia, cupos, expiración y mensajes sin datos | Si Redis falla, se cierra con `1013`; REST continúa como fuente de verdad. |
| Despliegue y respaldo | Manipulación, divulgación e indisponibilidad | Entornos y claves separados, perfil productivo estricto, respaldo cifrado y restauración de prueba | Los controles operativos dependen del runbook y del monitoreo externo. |
| Archivo técnico | Manipulación, elevación y repudio | Superusuario activo, motivo, inspección, huella, confirmación exacta, transacción e historial | No existe segunda aprobación para retiros de alto impacto. |

## Política ante fallos

- Autenticación, permisos, rol, reautenticación, descifrado y auditoría de
  revelado fallan cerrados.
- Redis no disponible impide comprobar límites. La API responde `503` y el
  WebSocket cierra con `1013`; nunca se omite el control.
- MySQL no disponible o un deadlock produce una respuesta genérica `503` con
  `request_id`. Las transacciones revierten los cambios.
- Una excepción interna produce `500` genérico con `request_id`. El cliente no
  recibe nombres de tablas, rutas ni trazas.
- Una falla de Channels no revierte una escritura ya confirmada. El navegador
  recupera la verdad mediante REST al reconectar.
- Una exportación no se entrega si no puede registrarse su auditoría.

## Abusos y límites

- Login: 10/min por IP y 5/15 min por usuario escrito.
- Revelado: 5/min por usuario autenticado.
- Exportaciones: 20/hora y máximo 5.000 registros por archivo.
- API: 1.200/hora por usuario autenticado.
- WebSocket: 20 conexiones por IP, 5 por usuario, 5 mensajes/segundo y 16 KiB
  por mensaje.
- Importación: límites configurables de archivo, ZIP, filas y columnas.

## Auditoría y alertas

`portal.security` emite JSON separado lógicamente del log de aplicación. El
recolector debe enrutarlo a un índice restringido. `SecurityAuditLog` conserva
los eventos consultables por soporte y no se expone en la API ni en Django
Admin.

Umbrales mínimos implementados:

| Evento | Umbral |
| --- | --- |
| Login fallido | 5 en 15 minutos por actor/IP |
| Acceso denegado | 10 en 5 minutos por actor/IP |
| Límite excedido | 3 en 10 minutos por actor/IP |
| Excepción interna | 5 en 5 minutos |
| Base no disponible | 3 en 5 minutos |
| Revelado de secretos | 10 en 60 minutos por actor/IP |

Al alcanzar el umbral se emite `security_alert_threshold_reached` con nivel
`CRITICAL`. El recolector de producción debe convertirlo en una notificación al
canal interno definido por Infraestructura.

Nunca se registran contraseñas, JWT, cookies, claves Fernet ni valores secretos.

## Decisiones pendientes

1. Doble aprobación para promover una cuenta a Administrador. Esfuerzo medio o
   alto; requiere solicitud, segundo aprobador y registro persistente.
2. Segunda aprobación para retiros técnicos con varias relaciones. Esfuerzo
   medio; cambia el procedimiento de soporte.
3. Almacenamiento inmutable o append-only del log de seguridad. Esfuerzo medio
   o alto; requiere separar permisos o usar un recolector externo.
4. Aprobar retención, responsables y canal de alertas antes de producción.

MFA permanece fuera de esta etapa y requiere evaluación independiente.
