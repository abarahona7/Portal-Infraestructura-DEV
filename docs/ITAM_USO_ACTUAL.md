# Uso actual de activos TI en DEV

El módulo de Equipos tiene un flujo visible simple:

1. **Tablero de Activos:** es la primera opción del menú Equipos y se abre al pulsar «Equipos». Muestra el total y los estados disponible, asignado, en préstamo, en reparación y de baja. Debajo reúne equipos que requieren revisión.
2. **Equipos:** abre la categoría del equipo para buscarlo o editar su ficha. «Abrir ficha y QR» muestra su garantía y datos actuales. El botón «Movimientos y comprobantes» abre el historial de ese equipo.
3. **Registrar movimiento:** selecciona tipo, equipo y colaborador cuando corresponde; revisa la vista previa y confirma. El portal guarda el movimiento, genera el folio y el PDF automáticamente. Puedes descargar el comprobante al terminar o más tarde desde el historial del equipo o del colaborador. «Cambio de equipo» aparece como tipo de movimiento y abre un formulario para elegir el equipo devuelto y el reemplazo; genera dos comprobantes vinculados.

No hay una pantalla separada de actas ni pasos de estado o firma en la interfaz. Los PDFs originales siguen guardados y las copias firmadas existentes se pueden descargar desde el historial. La carga de nuevas copias firmadas no está disponible en la interfaz simplificada. Los endpoints de consulta, estados, integridad y reportes permanecen en el backend para usos autorizados; la interfaz no los presenta como tareas de operación diaria.

La validación de QA queda pendiente hasta que exista el ambiente y se otorgue acceso. En DEV, `PYTHONPATH=. .venv/bin/python manage.py validar_integridad_itam --muestras 0` verifica en solo lectura los folios, PDFs, movimientos y eventos guardados.
