# Activos TI: Fase 1

La pantalla de Equipos mantiene el maestro de activos. Los nuevos equipos se registran disponibles; «Nuevo movimiento» permite asignar y devolver un equipo existente. Cada confirmación válida crea en una sola transacción MySQL el cambio de estado, el movimiento, el folio anual, el acta PDF y el registro de auditoría. El botón de documento en cada fila abre la trazabilidad básica y permite descargar cada acta persistida.

## Datos y compatibilidad

- Se ampliaron `Usuario` (RUT con dígito verificador, centro de costo, ubicación) y `Equipamiento` (estado físico, MAC, ubicación actual, UUID de QR y fecha de alta). Los 365 activos existentes conservaron su identidad y relación vigente.
- `MovimientoActivo` conserva origen/destino, estado, accesorios, ejecutor y un snapshot del momento. `ActaEntrega` conserva un snapshot documental y los bytes del PDF con SHA-256. Ambos registros se exponen solo en lectura después de crearse.
- `FolioContador` asigna `ATI-AAAA-######` mediante bloqueo de fila. El número se revierte si falla la transacción. El QR se reserva como identificador UUID; la ficha por QR corresponde a Fase 2.
- Los registros anteriores no se reescribieron como movimientos ITAM: su historial antiguo sigue en el portal. Los nuevos movimientos empiezan desde la puesta en uso de esta fase.
- Los formularios de equipo ya no asignan directamente ni modifican estado o ubicación. La API rechaza estos cambios; la baja de un colaborador con equipos requiere registrar devoluciones antes. La descarga anterior de `/api/usuarios/{id}/acta-entrega/` sigue disponible como resumen legado, mientras las nuevas actas numeradas se descargan desde `/api/actas/{id}/pdf/`.

## API

`POST /api/movimientos/` requiere un usuario autenticado con rol Operador Infraestructura o Administrador. Ejemplo de asignación:

```json
{
  "tipo_movimiento": "ASIGNACION",
  "activo_id": 142,
  "colaborador_destino_id": 87,
  "ubicacion_destino": "Oficina TI",
  "estado_fisico": "USADO",
  "accesorios_detalle": [{"nombre": "Cargador", "entregado": true}],
  "observaciones": "Equipo comprobado"
}
```

Para una devolución use `DEVOLUCION` y `colaborador_origen_id`, indicando cada accesorio recibido; si falta alguno, use `entregado: false` y una `nota`. Las asignaciones requieren RUT válido en la ficha del colaborador. El servidor valida de nuevo estado, colaborador y accesorios con la fila del activo bloqueada. `409` indica un conflicto de estado; `400` identifica datos incorrectos o incompletos. `GET /api/movimientos/?activo_id=142` muestra el histórico paginado. También admite `colaborador_id`.

## Validación y operación

El respaldo anterior está en `/home/tiangelo/migracion/portalinfra_dev_backup_pre_itam_20260929_162844.sql`; el respaldo previo a la migración 0052 quedó en `.local/backups/portalinfra_dev_backup_pre_itam_20260929_173406.sql` con permisos 600. Las migraciones 0050–0053 están aplicadas en MySQL DEV. La migración 0053 restauró los `BIGINT` originales de las claves primarias de DEV tras detectar que una versión previa de 0050 los redujo temporalmente a `INT`. La 0050 incluida en el repositorio ya evita esa reducción en instalaciones nuevas. Antes de esa corrección se generó un segundo respaldo en `.local/backups/portalinfra_dev_backup_pre_itam_20260929_175622.sql` (permisos 600). Para repetir la comprobación reversible, ejecute `python manage.py shell < scripts/validar_itam_transaccional.py`. El script crea datos temporales dentro de una transacción y verifica el rollback al terminar. También ejecutar `python manage.py validar_integridad_portal`, `npm run lint` y `npm run build` desde `siminfra-frontend`.

Las pruebas `core.test_asset_lifecycle` necesitan una base de pruebas MySQL. El usuario MySQL actual no tiene permiso para crear `test_portalinfra_dev` (error 1044), por lo que se validó el flujo en una transacción reversible sobre DEV. La concurrencia simultánea entre procesos sigue pendiente de probar en una base de pruebas con ese permiso.
