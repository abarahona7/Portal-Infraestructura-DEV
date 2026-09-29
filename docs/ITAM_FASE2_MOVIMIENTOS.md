# Activos TI: movimientos avanzados de Fase 2

El formulario «Nuevo movimiento» ahora ofrece reasignación, ingreso y salida de reparación y baja, además de asignación y devolución. Todos los movimientos generan una fila nueva e inmutable, acta PDF con folio anual, snapshot histórico y auditoría; el estado actual del activo se actualiza en la misma transacción. El identificador QR del activo no cambia.

| Movimiento | Estado inicial admitido | Colaboradores | Estado final |
| --- | --- | --- | --- |
| Asignación | Disponible, sin custodio | Destino activo con RUT | Asignado |
| Devolución | Asignado o en préstamo (también mantención legada con custodio) | Origen igual al custodio actual | Disponible o en reparación |
| Reasignación | Asignado o en préstamo | Origen igual al custodio actual; destino distinto, activo y con RUT | Asignado al nuevo custodio |
| Ingreso a reparación | Disponible o asignado/en préstamo | Si tiene custodio, debe indicarse como origen | En reparación, sin custodio |
| Salida de reparación | En reparación, sin custodio | Ninguno | Disponible |
| Baja | Disponible, sin custodio | Ninguno | Baja |

La reparación y la baja exigen observaciones. Para retirar un activo asignado hay que registrar primero su devolución o ingreso a reparación, y para darlo de baja después de una reparación hay que registrar la salida. Un activo en reparación o baja no se puede asignar. Los accesorios vigentes se validan en devolución, reasignación e ingreso a reparación desde un custodio; los faltantes requieren nota. La primera asignación verifica los accesorios del maestro, incluso si el activo pasó antes por reparación.

Las actas de movimientos sin colaborador tienen `colaborador` vacío mediante la migración 0054. El PDF de asignación y reasignación conserva la condición de custodia; los demás movimientos emiten una constancia de cambio de estado. En una reasignación, el documento y el movimiento registran custodio anterior y nuevo custodio. Los documentos emitidos previamente siguen guardados como bytes inmutables.

La migración 0054 se aplicó en MySQL DEV. El respaldo anterior a esta fase permanece en `.local/backups/portalinfra_dev_backup_pre_itam_20260929_175622.sql`; el respaldo posterior a 0054 está en `.local/backups/portalinfra_dev_backup_post_itam_0054_20260929_220612.sql`, ambos con permisos 600. Para verificar sin persistir datos: `python manage.py shell < scripts/validar_itam_transaccional.py` y `python manage.py shell < scripts/validar_itam_fase2_transaccional.py`. Ambas pruebas revierten sus cambios. La suite Django sigue sin poder crear `test_portalinfra_dev` por el permiso MySQL 1044, por lo que aún no se verificó concurrencia entre procesos en una base de pruebas.

Los tipos «Cambio de equipo» y «Préstamo», la firma del acta y las aprobaciones específicas por nuevos roles siguen fuera de este incremento.
