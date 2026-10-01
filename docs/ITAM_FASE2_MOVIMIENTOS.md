# Activos TI: movimientos avanzados de Fase 2

El flujo vigente, sin RUT personal ni ubicación física, se resume en [ITAM_SIMPLIFICACION.md](ITAM_SIMPLIFICACION.md).

El formulario «Nuevo movimiento» ahora ofrece reasignación, ingreso y salida de reparación y baja, además de asignación y devolución. Todos los movimientos generan una fila nueva e inmutable, acta PDF con folio anual, snapshot histórico y auditoría; el estado actual del activo se actualiza en la misma transacción. El identificador QR del activo no cambia.

| Movimiento | Estado inicial admitido | Colaboradores | Estado final |
| --- | --- | --- | --- |
| Asignación | Disponible, sin custodio | Destino activo | Asignado |
| Préstamo | Disponible, sin custodio | Destino activo | En préstamo |
| Devolución | Asignado o en préstamo (también mantención legada con custodio) | Origen igual al custodio actual | Disponible o en reparación |
| Reasignación | Asignado o en préstamo | Origen igual al custodio actual; destino distinto y activo | Asignado al nuevo custodio |
| Ingreso a reparación | Disponible o asignado/en préstamo | Si tiene custodio, debe indicarse como origen | En reparación, sin custodio |
| Salida de reparación | En reparación, sin custodio | Ninguno | Disponible |
| Baja | Disponible, sin custodio | Ninguno | Baja |
| Cambio de equipo | Equipo antiguo asignado o en préstamo; reemplazo disponible | Mismo custodio para ambos | Antiguo disponible o en reparación; reemplazo asignado |

La reparación y la baja exigen observaciones. Para retirar un activo asignado hay que registrar primero su devolución o ingreso a reparación, y para darlo de baja después de una reparación hay que registrar la salida. Un activo en reparación o baja no se puede asignar. Los accesorios vigentes se validan en devolución, reasignación e ingreso a reparación desde un custodio; los faltantes requieren nota. La primera asignación verifica los accesorios del maestro, incluso si el activo pasó antes por reparación.

El préstamo usa el mismo control de custodio y accesorios que una asignación y termina mediante devolución, reasignación o cambio de equipo. La fecha de vencimiento del préstamo no forma parte del modelo actual; requerirá una regla operativa definida antes de generar alertas de atraso.

El cambio se inicia desde «Registrar movimiento» en Equipos, eligiendo el tipo «Cambio de equipo». `POST /api/movimientos/cambio/` bloquea los dos activos en orden de ID y registra una `DEVOLUCION` del antiguo y un movimiento `CAMBIO` del reemplazo. Cada uno tiene folio y PDF propios, ambos comparten `operacion_id` (UUID), y cualquiera de las dos fichas permite abrir el cambio completo. `GET /api/movimientos/?operacion_id=<uuid>` recupera las dos partes. Ejemplo de solicitud:

```json
{
  "activo_origen_id": 142,
  "activo_destino_id": 215,
  "colaborador_id": 87,
  "estado_fisico_origen": "USADO",
  "estado_fisico_destino": "NUEVO",
  "estado_operativo_origen": "STOCK",
  "accesorios_devueltos": [{"nombre": "Cargador", "entregado": true}],
  "accesorios_entregados": [{"nombre": "Cable", "entregado": true}],
  "observaciones": "Renovación del equipo"
}
```

Si falla la segunda acta o alguna validación, se revierten ambos cambios y los folios.

Las actas de movimientos sin colaborador tienen `colaborador` vacío mediante la migración 0054. El PDF de asignación y reasignación conserva la condición de custodia; los demás movimientos emiten una constancia de cambio de estado. En una reasignación, el documento y el movimiento registran custodio anterior y nuevo custodio. Los documentos emitidos previamente siguen guardados como bytes inmutables.

Las migraciones 0054 y 0055 se aplicaron en MySQL DEV. La 0055 agrega `operacion_id` opcional e indexado a los movimientos; el respaldo previo está en `.local/backups/portalinfra_dev_backup_pre_itam_0055_20260929_222846.sql` (permisos 600). El respaldo anterior a esta fase permanece en `.local/backups/portalinfra_dev_backup_pre_itam_20260929_175622.sql`; el respaldo posterior a 0054 está en `.local/backups/portalinfra_dev_backup_post_itam_0054_20260929_220612.sql`, ambos con permisos 600. Para verificar sin persistir datos: `python manage.py shell < scripts/validar_itam_transaccional.py` y `python manage.py shell < scripts/validar_itam_fase2_transaccional.py` y `python manage.py shell < scripts/validar_itam_prestamo_cambio.py`. Las tres pruebas revierten sus cambios. La suite Django sigue sin poder crear `test_portalinfra_dev` por el permiso MySQL 1044, por lo que aún no se verificó concurrencia entre procesos en una base de pruebas.

La firma del acta, el vencimiento de préstamos y las aprobaciones específicas por nuevos roles siguen fuera de este incremento.
