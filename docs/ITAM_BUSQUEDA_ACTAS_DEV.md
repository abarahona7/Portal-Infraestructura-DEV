# Consulta de actas ITAM por folio en DEV

El Tablero de Activos permite localizar un acta por su folio completo `ATI-AAAA-######`. La búsqueda muestra tipo, fecha y estado vigente, y permite descargar el PDF original, la copia firmada si existe y abrir la gestión del acta. Incluye actas generadas, pendientes de firma, firmadas, cerradas y anuladas; no altera el documento ni inventa un folio para las actas legadas anteriores a ITAM.

`GET /api/actas/?folio=ATI-2026-000001` busca por coincidencia exacta sobre el índice único existente. Acepta minúsculas y espacios exteriores, valida el formato y usa los permisos actuales de actas (Operador Infraestructura o Administrador). La respuesta impide caché. No requiere migración.

El respaldo anterior quedó en `.local/backups/portalinfra_dev_backup_pre_itam_busqueda_actas_20260930_142722.sql`. En DEV se valida con `.venv/bin/python manage.py shell < scripts/validar_busqueda_acta_folio_itam.py`: crea un acta real de alta, comprueba búsqueda, PDF, cambio de estado y permisos, y revierte todos los datos. QA continúa pendiente de ambiente y acceso.
