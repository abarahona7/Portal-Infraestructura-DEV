# Ambigüedades revisadas antes de QA y producción

Revisión del código y los documentos al 5 de octubre de 2026. «Confirmado»
describe el comportamiento actual; «pendiente» requiere una decisión, un cambio
o una prueba en el ambiente real. Esta lista complementa el
[runbook de producción](../PRODUCTION_RUNBOOK.md).

| # | Punto | Hallazgo y acción pendiente |
| --- | --- | --- |
| 1 | Módulos del Operador | **Confirmado:** puede consultar Usuarios, Departamentos/Áreas, Equipos, Tablero, Ficha QR, PCs genéricos, Gestión de IP, Servidores, Anexos y Perfiles genéricos. Puede crear, editar, asignar y exportar donde existe esa acción. No puede borrar ni revelar secretos. No hay otro módulo operativo «deshabilitado» para ese rol. Validar la matriz de roles en QA. |
| 2 | Tablero y QR ausentes del mapa anterior | **Confirmado:** ambos requieren sesión y rol Operador o Administrador; Visualizador no accede. El diagrama PNG/SVG de septiembre es anterior a la reconstrucción y queda marcado como histórico en `ACCIONES_ACTUALES.md`. Verificar en QA acceso directo al QR con cada rol y regenerar el diagrama antes de entregar documentación gráfica definitiva. |
| 3 | Reactivación de `BAJA` | **Confirmado:** volver a `ACTIVO` no recupera automáticamente IP ni anexo. La señal del usuario sí puede volver a enlazar un Notebook o Mac sin usuario cuyo hostname coincida con el del usuario; no restaura por historial los demás equipos. **Pendiente:** decidir si ese enlace automático es el comportamiento deseado y probar baja/reactivación en QA antes de publicar. |
| 4 | IP de Servidores | **Confirmado en backend:** `ServidorSerializer` y el servicio de asignación exigen una IP libre de `172.23.1.0/24`, excluyendo dirección de red y broadcast. La API rechaza otros segmentos; existe una prueba automatizada para ello. |
| 5 | Eliminación de IP y `CASCADE` | **Confirmado:** el endpoint de borrado impide eliminar IP vinculada a usuario, servidor, PC genérico o asignación activa; al liberar el vínculo, el Administrador puede borrarla. El `on_delete=CASCADE` de `AsignacionIP.ip` puede borrar esa asignación si una IP se elimina por otra vía del ORM. **Pendiente:** endurecer el endpoint para exigir explícitamente `estado=LIBRE` incluso si los datos quedaran desincronizados y evitar borrados directos por scripts. |
| 6 | `loaddata` sobre destino no vacío | **Sin protección técnica específica del proyecto:** el runbook exige destino vacío, pero el comando estándar `loaddata` sigue siendo ejecutable. **Pendiente antes de importar:** incorporar una comprobación automática de vacío o un comando de carga protegido; hasta entonces, Infraestructura debe verificar y registrar que el destino no contiene datos operacionales. Nunca usar `loaddata` para actualizar una base productiva existente. |
| 7 | Rama de despliegue | **Confirmado:** la reconstrucción está en `feature/itam-reinicio-limpio`, 13 commits delante de `main` al momento de esta revisión. El runbook se refiere a `origin/main` como destino final, no como estado ya alcanzado. **Pendiente:** completar QA, revisar los cuatro cambios locales sin commit de formularios, abrir/revisar la integración y promover el commit aprobado a `main` antes de desplegarlo. |
| 8 | Validación manual | **Pendiente en QA y entorno definitivo:** escanear físicamente QR con usuario asignado y sin usuario; revisar visualmente el PDF del acta y su RUT manuscrito; abrir los Excel exportados en una hoja de cálculo; comprobar dominio, certificado y proxy HTTPS reales, incluida la apertura directa de `/qr/a/<uuid>`. Las pruebas automáticas simulan estos flujos, pero no sustituyen estas comprobaciones. |

Los puntos 3, 5, 6, 7 y 8 son puertas de salida: deben quedar resueltos o
aprobados con evidencia antes de declarar el portal listo para producción.
