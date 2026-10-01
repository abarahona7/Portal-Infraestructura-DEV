# Períodos de custodia por colaborador

La ficha del colaborador muestra los activos vigentes y, por separado, los períodos anteriores de custodia. Cada período expone la fecha de entrega, la fecha de salida, el tipo de movimiento y los folios de ambas actas cuando existen. Se pueden descargar las actas y abrir el historial del activo desde esa vista. En la lista de movimientos del colaborador, cada acta permite además descargar directamente la copia firmada cuando exista y abrir su gestión para revisar estados e integridad.

`GET /api/movimientos/custodias/?colaborador_id=<id>` construye esta lectura desde los movimientos ITAM inmutables, ordenados cronológicamente por activo. Una asignación, préstamo o reasignación hacia el colaborador abre el período; una devolución, reasignación desde él o ingreso a reparación lo cierra. El cambio de equipo queda representado por la devolución del antiguo y la entrega del reemplazo. La API mantiene los permisos de lectura de movimientos.

Si un activo ya estaba asignado antes de la trazabilidad ITAM, el período se marca `LEGADO`. Puede conservar la fecha de asignación del maestro, pero no inventa folio ni PDF de entrega. Si ese activo se devuelve después, se muestra el acta real de salida. Una asignación sin cierre registrado que ya no coincide con el custodio actual aparece marcada `SIN_CIERRE_REGISTRADO` para revisión, sin atribuirle una devolución inexistente.

No hay migración ni escritura persistente para este incremento. En DEV se valida con `.venv/bin/python manage.py shell < scripts/validar_custodias_colaborador.py`, que comprueba los casos ITAM y legados dentro de una transacción revertida. QA continúa pendiente de ambiente y permisos.
