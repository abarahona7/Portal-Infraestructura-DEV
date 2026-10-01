# Consulta de actas ITAM por folio en DEV

La búsqueda por folio completo `ATI-AAAA-######` permanece en la API, pero ya no tiene pantalla propia en el portal. Para el uso diario, el comprobante se descarga desde el movimiento asociado en el historial del equipo o colaborador. La API incluye actas generadas, pendientes de firma, firmadas, cerradas y anuladas; no altera documentos ni inventa folios para movimientos legados.

`GET /api/actas/?folio=ATI-2026-000001` busca por coincidencia exacta sobre el índice único existente. Acepta minúsculas y espacios exteriores, valida el formato y usa los permisos actuales de actas (Operador Infraestructura o Administrador). La respuesta impide caché. No requiere migración.

El respaldo anterior quedó en `.local/backups/portalinfra_dev_backup_pre_itam_busqueda_actas_20260930_142722.sql`. En DEV se valida con `.venv/bin/python manage.py shell < scripts/validar_busqueda_acta_folio_itam.py`: crea un acta real de alta, comprueba búsqueda, PDF, cambio de estado y permisos, y revierte todos los datos. QA continúa pendiente de ambiente y acceso.
