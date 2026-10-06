# Actualización del portal a MySQL 8.4

El backend usa Django 6.0.8 y `mysqlclient` 2.2.8. La configuración actual usa
`utf8mb4`, transacciones `READ COMMITTED` y modo SQL estricto. No hace falta
cambiar modelos, contraseñas del portal ni recrear la base solo por actualizar
el servidor a MySQL 8.4.

El 6 de octubre de 2026 se comprobó inicialmente en DEV, mediante consultas, que
`portalinfra_dev` responde con MySQL `8.4.11-google`, conexión TLS, `utf8mb4`,
colación `utf8mb4_0900_ai_ci`, `STRICT_TRANS_TABLES` y `READ-COMMITTED`. Sus 31
tablas usan esa misma colación. `manage.py check --database default` terminó sin
errores. El cliente MySQL y la biblioteca cargada por `mysqlclient` son 8.4.11.
`validar_integridad_portal` confirmó las 21 reglas funcionales sin errores.

## Qué cambió en el proyecto

Docker Compose y la validación de GitHub Actions usan `mysql:8.4`. Compose
configura `utf8mb4_0900_ai_ci`, igual que DEV. Cambiar la configuración del
servidor **no convierte por sí solo** las columnas existentes. Las pruebas de
`core` usan una base temporal MySQL 8.4 creada por
`scripts/run_qa_mysql.py`; nunca deben ejecutarse contra la base compartida.
La suite completa pasó: 161 pruebas, 2 omisiones y 0 fallos.

## Antes de reiniciar un MySQL propio

Si se usa el servicio `db` de Docker Compose y su volumen `mysql_data` ya tiene
datos de MySQL 8.0, **no ejecutar `docker compose up -d db` inmediatamente**:
al arrancar con la imagen 8.4 podría actualizar el formato del volumen. Primero
confirmar el contenedor y el volumen utilizados, guardar un respaldo completo
fuera del servidor, restaurarlo en una instancia aislada, comprobar conteos y
planear una ventana con Infraestructura. No borrar ni recrear `mysql_data` para
resolver un error de conexión. Si se usa la instancia MySQL administrada de DEV,
este servicio Compose no participa en esa actualización.

MySQL 8.4 deshabilita `mysql_native_password` por defecto. Si alguna cuenta
deja de conectar con un error de plugin, Infraestructura debe revisar el método
de autenticación y migrarla a `caching_sha2_password`; no corresponde cambiar
el código ni activar el plugin antiguo permanentemente. La conexión actual de
DEV ya funciona, por lo que no hay motivo para cambiar su cuenta o clave.

## Comprobaciones de DEV tras la actualización

Desde la raíz del proyecto, con el `.env` correcto y el entorno virtual activo:

```bash
.venv/bin/python manage.py check --database default
.venv/bin/python manage.py showmigrations --plan
.venv/bin/python manage.py migrate --check
```

`migrate --check` no aplica cambios; devuelve código distinto de cero si faltan
migraciones. DEV tenía pendientes `core.0059` y `core.0060`. Antes de aplicarlas
se comprobó que `core.0059` actualizaría 42 claves normalizadas, sin colisiones,
y agregaría una columna e índice de auditoría. `core.0060` cambia la protección
de borrado en el ORM, sin SQL de alteración de tabla.

Se creó un respaldo de `portalinfra_dev` en
`.local/backups/portalinfra_dev_pre_0059_0060_20261006_150252.sql.gz`, con
permisos `600` y SHA-256
`d203eceaf713416c7ef43d9d543e02246cad6002c8397691f2fbaf01ee4e1b75`.
Se restauró en un MySQL 8.4 temporal: ambas migraciones, la integridad y el
descifrado de secretos pasaron. Los conteos de 30 tablas y la huella de ID/QR
de los 365 equipos coincidieron antes y después. El contenedor se retiró.

Después se aplicaron `core.0059` y `core.0060` en DEV sin borrar ni recrear la
base. `migrate --check` y `check --database default` pasaron; también las 21
reglas de integridad y el descifrado de 369 secretos. Permanecen 365 equipos,
con 365 QR únicos y ninguno nulo. QA y producción requieren su propio respaldo,
ensayo y migración; no apuntar esos ambientes a `portalinfra_dev`.

Referencias del fabricante: [preparación y respaldo antes de actualizar](https://dev.mysql.com/doc/refman/8.4/en/upgrade-before-you-begin.html)
y [cambio de autenticación en 8.4](https://dev.mysql.com/doc/refman/8.4/en/native-pluggable-authentication.html).

Después de aplicar las migraciones en el ambiente correspondiente, ejecutar
`migrate --check`, `validar_integridad_portal` y una prueba manual de inicio de
sesión, listado de usuarios, equipos, IP, QR y acta. Para producción se requiere
además la validación completa del [runbook](../PRODUCTION_RUNBOOK.md) en una
base de QA independiente; DEV no reemplaza esa etapa.
