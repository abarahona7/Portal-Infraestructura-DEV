# Seguimiento de actas por firmar en DEV

El backend conserva el conteo y la cola paginada de actas en estado vigente `GENERADA` o `PENDIENTE_FIRMA`, pero el Tablero simplificado ya no muestra esa lista ni una gestión de estados. La interfaz sólo permite descargar el comprobante desde el movimiento y descargar una copia firmada si ya existía. Por ahora, no permite cargar nuevas copias firmadas; la transición de estados sigue disponible en la API para usos autorizados.

El estado vigente se obtiene del último evento inmutable del acta, sin reescribir el documento emitido. `GET /api/actas/pendientes/?page=1&page_size=20` usa los permisos actuales de actas y devuelve folio, tipo, fecha y estado, sin incluir PDF ni datos personales. La respuesta impide caché. El resumen `GET /api/activos/resumen/` agrega el contador y ocho actas recientes. No hay migración nueva ni notificaciones automáticas.

La prueba reversible `.venv/bin/python manage.py shell < scripts/validar_actas_pendientes_transaccional.py` crea tres actas temporales, avanza una a pendiente y firma otra; comprueba resumen, paginación, autenticación y reversión. El respaldo previo está en `.local/backups/portalinfra_dev_backup_pre_itam_pendientes_firma_20260930_112651.sql`. QA sigue pendiente de la existencia y acceso al ambiente.
