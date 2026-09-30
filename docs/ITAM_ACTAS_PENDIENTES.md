# Seguimiento de actas por firmar en DEV

El Tablero de Activos muestra cuántas actas siguen en estado vigente `GENERADA` o `PENDIENTE_FIRMA`, las ocho más recientes y una lista completa paginada. Cada fila abre la gestión del acta para enviarla a firma o registrar su copia PDF firmada. Al cambiar el estado se actualiza el tablero; las actas `FIRMADA`, `CERRADA` o `ANULADA` dejan de figurar como pendientes.

El estado vigente se obtiene del último evento inmutable del acta, sin reescribir el documento emitido. `GET /api/actas/pendientes/?page=1&page_size=20` usa los permisos actuales de actas y devuelve folio, tipo, fecha y estado, sin incluir PDF ni datos personales. La respuesta impide caché. El resumen `GET /api/activos/resumen/` agrega el contador y ocho actas recientes. No hay migración nueva ni notificaciones automáticas.

La prueba reversible `.venv/bin/python manage.py shell < scripts/validar_actas_pendientes_transaccional.py` crea tres actas temporales, avanza una a pendiente y firma otra; comprueba resumen, paginación, autenticación y reversión. El respaldo previo está en `.local/backups/portalinfra_dev_backup_pre_itam_pendientes_firma_20260930_112651.sql`. QA sigue pendiente de la existencia y acceso al ambiente.
