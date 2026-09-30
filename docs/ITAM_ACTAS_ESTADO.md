# Ciclo de estados de actas ITAM (DEV)

El acta emitida conserva su folio, PDF original, SHA-256 y snapshot sin cambios. La API calcula el estado vigente desde eventos inmutables asociados al acta; por ello el campo `ActaEntrega.estado` almacenado sigue en `GENERADA` para actas emitidas. No se debe usar ese campo directamente para informes del estado vigente: usar el serializador de la API o el servicio `estado_vigente`.

Flujo: `GENERADA → PENDIENTE_FIRMA → FIRMADA → CERRADA`. Un administrador puede registrar `ANULADA` desde cualquier estado previo con motivo obligatorio, incluso después del cierre, sin borrar el historial. El paso a `FIRMADA` requiere cargar una copia PDF de hasta 10 MB. El portal conserva el archivo, su SHA-256, actor y fecha. Esta carga es una declaración operacional: el portal no valida la identidad del firmante ni certifica la firma.

Endpoints autenticados:

- `GET /api/actas/{id}/` devuelve estado vigente, fecha de cierre y presencia de copia firmada.
- `GET /api/actas/{id}/eventos/` devuelve la secuencia de transiciones, actor, motivo y hash de la copia.
- `POST /api/actas/{id}/estado/` recibe `estado_nuevo`, `motivo` y, al marcar `FIRMADA`, `archivo_firmado` en multipart.
- `GET /api/actas/{id}/pdf/` descarga el original; `GET /api/actas/{id}/firmada/` descarga la copia cargada.

Los operadores pueden avanzar el flujo; solo administradores pueden anular. Las transiciones concurrentes se serializan bloqueando el acta. En DEV se aplicó la migración 0056 con respaldo previo en `.local/backups/`. Validar con `.venv/bin/python manage.py shell < scripts/validar_actas_estado_transaccional.py`; el script revierte sus datos al finalizar. QA sigue pendiente de ambiente y permisos.
