# Archivo de actas ITAM en DEV

El Tablero de Activos tiene una consulta paginada de todas las actas ITAM, con filtros opcionales por estado vigente y tipo de movimiento. La lista se carga solo al pulsar «Consultar» y permite descargar el original, descargar la copia firmada cuando exista y abrir la gestión del acta. Si un cambio de estado hace que el acta deje de cumplir el filtro, la lista se actualiza desde la primera página.

`GET /api/actas/?estado=CERRADA&tipo_movimiento=ASIGNACION&page=1&page_size=20` calcula el estado desde el último evento inmutable. No filtra por el estado inicial del documento. Los parámetros inválidos reciben `400`; los filtros existentes por folio y colaborador siguen disponibles y se pueden combinar. Se mantiene el permiso de actas (Operador Infraestructura o Administrador), la paginación y `Cache-Control: no-store, private`. No se añadió migración ni se modificaron actas existentes.

El respaldo previo está en `.local/backups/portalinfra_dev_backup_pre_itam_archivo_actas_20260930_222857.sql`. La validación reversible `.venv/bin/python manage.py shell < scripts/validar_busqueda_acta_folio_itam.py` crea un acta real, la lleva por los estados generada, pendiente, firmada y cerrada, y comprueba los filtros, las descargas y los permisos antes de revertirla. QA continúa pendiente de ambiente y acceso.
