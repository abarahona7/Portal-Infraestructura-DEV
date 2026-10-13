# Archivo técnico y protocolos de cambios

Los usuarios del portal, incluido el rol Administrador, no pueden eliminar ni restaurar registros. La API rechaza `DELETE` y ya no publica los endpoints de Papelera. El estado operativo **Baja** sigue siendo distinto del archivado: cambiarlo aplica sus protocolos y reglas de liberación existentes.

## Solicitud y revisión técnica

Cuando un registro deba retirarse, el solicitante entrega al equipo técnico el módulo, ID y motivo por el canal de soporte vigente. La solicitud por sí sola no modifica el portal. No existe un flujo adicional de aprobaciones dentro de la aplicación.

Un técnico con acceso al servidor y una cuenta Django de superusuario activa inspecciona primero el registro:

```bash
.venv/bin/python manage.py gestionar_archivo inspeccionar usuarios 123 --actor tecnico
```

La salida muestra las relaciones actuales y una `huella`. Para un usuario incluye equipos, IP y anexos; para un equipo, custodio y estado; para servidores y PCs genéricos, IP; para departamentos y áreas, sus dependencias. El archivo de un departamento o área con dependencias activas se bloquea. Una IP solo puede archivarse cuando está libre y sin asignaciones.

Tras revisar el impacto, el técnico ejecuta el retiro con el mismo módulo, ID y huella:

```bash
.venv/bin/python manage.py gestionar_archivo archivar usuarios 123 \
  --actor tecnico --motivo 'Solicitud TI-123: retiro aprobado' \
  --huella HUELLA_REEMPLAZAR --confirmar ARCHIVAR:usuarios:123
```

Sustituye `HUELLA_REEMPLAZAR` por el valor completo que entregó `inspeccionar`. Si cambió una relación entre la inspección y el archivo, el comando se detiene y exige inspeccionar de nuevo. El retiro es transaccional: el registro conserva su ID y datos, se oculta de la operación diaria y se guardan motivo, responsable, fecha y fotografía de relaciones en el historial técnico. Las claves únicas siguen reservadas.

**El archivo puede liberar relaciones.** Un usuario libera equipos, IP y anexo; un equipo libera su custodio; un servidor o PC genérico libera la IP. Esto solo ocurre al ejecutar el retiro técnico, no al recibir la solicitud. El historial de los módulos sigue registrando el movimiento. El QR del equipo archivado deja de resolver su ficha y vuelve a funcionar al restaurar el registro.

## Restauración y reporte

Antes de restaurar, inspecciona el registro archivado y sus relaciones previas:

```bash
.venv/bin/python manage.py gestionar_archivo inspeccionar usuarios 123 --actor tecnico
.venv/bin/python manage.py gestionar_archivo restaurar usuarios 123 \
  --actor tecnico --motivo 'Solicitud TI-124: restauración aprobada' \
  --confirmar RESTAURAR:usuarios:123
```

La restauración no reasigna recursos automáticamente: una IP o equipo liberado puede pertenecer ya a otro registro. Revisa la fotografía y realiza cada asignación desde los módulos normales. Si el departamento o área padre también está archivado, restáuralo primero.

El reporte técnico incluye los registros aún archivados **y todos los eventos de archivo/restauración**, incluso de registros ya restaurados. Se genera como JSON en un archivo nuevo con permisos `0600`:

```bash
install -d -m 700 .local/reportes
.venv/bin/python manage.py gestionar_archivo reporte usuarios \
  --actor tecnico --salida .local/reportes/archivo_usuarios_20261013.json
```

Omite `usuarios` para incluir todos los módulos. Protege ese archivo como información interna y bórralo cuando ya no se necesite. Los retiros anteriores a este cambio conservan sus eventos existentes, aunque no tendrán la nueva fotografía detallada de relaciones.

Antes de aplicar la migración `0063`, realiza y verifica un respaldo de la base existente. El archivo técnico conserva filas en la misma base; los respaldos independientes son necesarios para recuperarse de una pérdida o corrupción de esa base.
