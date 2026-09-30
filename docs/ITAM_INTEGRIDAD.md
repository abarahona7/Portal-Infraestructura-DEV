# Verificación de integridad ITAM

En DEV se puede ejecutar `PYTHONPATH=. .venv/bin/python manage.py validar_integridad_itam` para revisar, sin escribir en la base de datos, los folios ATI, sus contadores anuales, el PDF original y su SHA-256, el snapshot emitido, la relación entre acta y movimiento, la secuencia de estados y el hash de la copia PDF firmada. El comando devuelve un error si encuentra inconsistencias. `--muestras 0` omite los IDs de ejemplo; por defecto muestra hasta diez IDs por regla, sin exponer documentos ni datos personales.

El validador comprueba la integridad de los bytes guardados frente a sus hashes, pero no certifica la autenticidad de una firma manuscrita. Una diferencia de hash requiere investigar el dato y el respaldo antes de cualquier corrección. El comando no repara ni modifica registros.

La prueba reversible `PYTHONPATH=. .venv/bin/python manage.py shell < scripts/validar_integridad_itam_transaccional.py` crea un préstamo con acta y copia firmada, verifica que el caso válido pase, introduce anomalías sintéticas y confirma que se detecten. Todo ocurre dentro de una transacción que se revierte. La validación general del portal se ejecuta en la misma prueba para comprobar que el estado `PRESTAMO` se acepta.
