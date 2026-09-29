# Tablero de activos TI en DEV

La sección «Equipos → Tablero de Activos» resume el maestro completo de `Equipamiento`, incluidos los activos anteriores al módulo ITAM. Muestra total, disponibles, asignados, en reparación, en préstamo y dados de baja; también identifica activos sin serie, sin activo fijo y con custodio no activo. Las distribuciones por tipo, ubicación y área asignada presentan las diez categorías principales más «Otros». Los últimos ocho movimientos muestran folio y permiten abrir el historial o descargar el acta.

`GET /api/activos/resumen/` calcula los indicadores en MySQL y requiere el mismo rol de lectura de Equipos (Operador Infraestructura o Administrador). No crea ni modifica registros. El navegador solicita los datos al abrir el tablero o al pulsar «Actualizar», y la respuesta usa `Cache-Control: no-store`. El contador de movimientos de los últimos 30 días empieza con la nueva trazabilidad: no reconstruye documentos ni movimientos antiguos.

No se requiere migración ni infraestructura QA para este incremento. En DEV se verificó con `python manage.py shell < scripts/validar_dashboard_itam.py`, que crea datos temporales dentro de una transacción, comprueba conteos, distribuciones y permisos, y revierte todo. Para la comprobación general: `python manage.py validar_integridad_portal`, `npm run lint` y `npm run build` desde `siminfra-frontend`.

Quedan para próximas etapas las alertas programadas, garantías y aprobaciones, que requieren definir fuentes de datos y reglas operativas con el equipo TI. La validación en QA se hará cuando exista el ambiente y se gestione acceso al servidor y la aplicación.
