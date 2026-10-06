# Ambigüedades revisadas antes de QA y producción

Revisión del código y los documentos al 6 de octubre de 2026. «Confirmado»
describe el comportamiento actual; «pendiente» requiere una decisión, un cambio
o una prueba en el ambiente real. Esta lista complementa el
[runbook de producción](../PRODUCTION_RUNBOOK.md).

| # | Punto | Hallazgo y acción pendiente |
| --- | --- | --- |
| 1 | Módulos del Operador | **Confirmado:** puede consultar Usuarios, Departamentos/Áreas, Equipos, Tablero, Ficha QR, PCs genéricos, Gestión de IP, Servidores, Anexos y Perfiles genéricos. Puede crear, editar, asignar y exportar donde existe esa acción. No puede borrar ni revelar secretos. No hay otro módulo operativo «deshabilitado» para ese rol. Validar la matriz de roles en QA. |
| 2 | Tablero y QR ausentes del mapa anterior | **Confirmado:** ambos requieren sesión y rol Operador o Administrador; Visualizador no accede. Se retiró el diagrama obsoleto de septiembre y `ACCIONES_ACTUALES.md` describe el comportamiento vigente. Verificar en QA acceso directo al QR con cada rol. |
| 3 | Reactivación de `BAJA` | **Confirmado:** volver a `ACTIVO` no recupera automáticamente IP ni anexo. La señal del usuario sí puede volver a enlazar un Notebook o Mac sin usuario cuyo hostname coincida con el del usuario; no restaura por historial los demás equipos. **Pendiente:** decidir si ese enlace automático es el comportamiento deseado y probar baja/reactivación en QA antes de publicar. |
| 4 | IP de Servidores | **Confirmado en backend:** `ServidorSerializer` y el servicio de asignación exigen una IP libre de `172.23.1.0/24`, excluyendo dirección de red y broadcast. La API rechaza otros segmentos; existe una prueba automatizada para ello. |
| 5 | Eliminación de IP y `CASCADE` | **Resuelto en código:** el endpoint solo borra una IP `LIBRE` sin dueño ni asignación activa, con bloqueo de fila durante la comprobación. La migración 0060 cambia `AsignacionIP.ip` a `PROTECT` para impedir que una eliminación directa por ORM borre la asignación. Falta aplicar y validar la migración en QA. |
| 6 | `loaddata` sobre destino no vacío | **Resuelto en código:** el comando del portal rechaza una base con usuarios o registros de `core`, y acepta una base operacional vacía. Antes de importar sigue siendo obligatorio confirmar la conexión y el destino; nunca usarlo para actualizar una base productiva existente. Falta validar el procedimiento en QA. |
| 7 | Rama de despliegue | **Confirmado:** la reconstrucción sigue en `feature/itam-reinicio-limpio`. El runbook se refiere a `origin/main` como destino final, no como estado ya alcanzado. **Pendiente:** completar QA, revisar la integración y promover el commit aprobado a `main` antes de desplegarlo. |
| 8 | Validación manual | **Pendiente en QA y entorno definitivo:** escanear físicamente QR con usuario asignado y sin usuario; revisar visualmente el PDF del acta y su RUT manuscrito; abrir los Excel exportados en una hoja de cálculo; comprobar dominio, certificado y proxy HTTPS reales, incluida la apertura directa de `/qr/a/<uuid>`. Las pruebas automáticas simulan estos flujos, pero no sustituyen estas comprobaciones. |
| 9 | Líneas móviles duplicadas en DEV | **Pendiente de conciliación:** dos números aparecen cada uno en celulares asignados a usuarios diferentes (equipos 44/101 y 93/204). La API impide crear nuevos conflictos y `validar_integridad_portal` identifica los cuatro registros, sin alterarlos. Confirmar con Infraestructura TI quién conserva cada línea y actualizar solo los datos incorrectos antes de repetir la validación. |

Los puntos 3, 7, 8 y 9, más la validación en QA de los cambios 5 y 6, son puertas
de salida antes de declarar el portal listo para producción.
