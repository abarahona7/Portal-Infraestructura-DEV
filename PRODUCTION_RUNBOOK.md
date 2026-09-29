# Despliegue de producción

Este procedimiento publica el portal con MySQL 8, HTTPS y el perfil
`config.settings_production`. Los secretos reales se guardan únicamente en el
`.env` del servidor y nunca se agregan a Git.

## 1. Preparar el servidor

1. Instalar Python, las dependencias de `requirements.txt`, Node.js y MySQL 8.
2. Copiar `.env.production.example` como `.env`.
3. Reemplazar cada valor `replace-with`.
4. Generar valores independientes para Django y Fernet:

```powershell
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
.\venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`FIELD_ENCRYPTION_KEY` debe conservarse en un almacén seguro y formar parte del
procedimiento de recuperación. Sin esa clave no se pueden revelar los secretos
cifrados existentes.

## 2. Preparar MySQL

Para ejecutar MySQL localmente mediante Docker:

```powershell
docker compose up -d db
docker compose ps
```

El puerto queda publicado solamente en `127.0.0.1` de forma predeterminada. Si
MySQL se administra fuera de Docker, configurar `DATABASE_HOST`,
`DATABASE_PORT` y, cuando corresponda, `DATABASE_SSL_CA`.

Antes de continuar, validar la conexión:

```powershell
.\venv\Scripts\python.exe manage.py check --database default --settings=config.settings_production
```

En una instancia MySQL aislada para pruebas, ejecutar también:

```powershell
.\venv\Scripts\python.exe manage.py test core.test_ip_assignment_service --settings=config.settings_production
```

Esta suite incluye rollback con fallos inyectados y dos asignaciones simultáneas
sobre una misma IP. No debe ejecutarse contra la base productiva; Django crea y
elimina una base de pruebas temporal.

## 3. Migrar desde SQLite

Realizar esta operación durante una ventana sin modificaciones en el portal.
El procedimiento ampliado, su validación por huellas y la vuelta atrás están en
[docs/MIGRACION_MYSQL.md](docs/MIGRACION_MYSQL.md).

1. Detener el backend actual.
2. Respaldar `db.sqlite3`, `.env` y `FIELD_ENCRYPTION_KEY` fuera del directorio
   de despliegue.
3. Auditar el origen y exportar los datos usando temporalmente el perfil de
   desarrollo:

```powershell
.\venv\Scripts\python.exe manage.py auditar_migracion_db --salida auditoria-sqlite.json
.\venv\Scripts\python.exe manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude admin.logentry --exclude sessions.session --exclude token_blacklist --exclude core.portalsession --indent 2 --output portal-pre-mysql.json
```

4. Activar el `.env` productivo y crear el esquema e importar:

```powershell
.\venv\Scripts\python.exe manage.py migrate --settings=config.settings_production
.\venv\Scripts\python.exe manage.py loaddata portal-pre-mysql.json --settings=config.settings_production
.\venv\Scripts\python.exe manage.py auditar_migracion_db --salida auditoria-mysql.json --comparar auditoria-sqlite.json --settings=config.settings_production
.\venv\Scripts\python.exe manage.py verify_secrets --settings=config.settings_production
```

5. No habilitar el acceso si la comparación de conteos, relaciones, huellas o
   migraciones informa una diferencia. Las sesiones se excluyen deliberadamente
   y todos los operadores deben autenticarse nuevamente.
6. Eliminar del servidor el JSON de migración cuando el respaldo definitivo ya
   esté verificado, porque puede contener información operacional.

## 4. Validar el backend

```powershell
.\venv\Scripts\python.exe manage.py check --deploy --settings=config.settings_production
.\venv\Scripts\python.exe manage.py migrate --check --settings=config.settings_production
.\venv\Scripts\python.exe manage.py validar_integridad_portal --settings=config.settings_production
.\venv\Scripts\python.exe manage.py collectstatic --noinput --settings=config.settings_production
```

Un valor obligatorio ausente, SQLite, `DEBUG=True`, una clave inválida o una
cookie insegura impiden que el perfil productivo inicie.

`SECURE_HSTS_PRELOAD=False` mantiene la advertencia opcional `security.W021`.
Solo debe cambiarse a `True` cuando el dominio definitivo y todos sus
subdominios cumplan permanentemente HTTPS y se haya aprobado su incorporación
a la lista preload de los navegadores.

## 5. Compilar el frontend

Configurar `siminfra-frontend/.env.local` para que la API use el mismo dominio:

```env
VITE_API_URL=/api
```

Después compilar:

```powershell
cd siminfra-frontend
npm ci
npm run lint
npm run build
```

El proxy HTTPS debe servir `dist`, enviar `/api` al backend y servir
`staticfiles` como contenido estático. Mantener frontend y API bajo el mismo
origen permite que Axios envíe el token CSRF sin exponerlo a otros dominios.

## 6. Ejecutar el backend

No utilizar `runserver` en producción. En Windows se incluye Waitress como
servidor WSGI; debe escuchar solamente en la interfaz accesible por el proxy:

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings_production'
.\venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 --threads=8 config.wsgi:application
```

El proxy debe reemplazar `X-Forwarded-Proto` y evitar que el cliente se conecte
directamente a Waitress. Solo después de confirmar HTTPS en todo el sitio se
debe habilitar HSTS.

En producción los logs se escriben como JSON en la salida estándar. Cada
respuesta incluye `X-Request-ID`, y el mismo valor aparece en los logs internos
del ciclo de esa solicitud. El recolector de logs debe conservar este campo y
restringir el acceso a los registros.

## 7. Verificación funcional

1. Iniciar sesión y recargar la página sin perder la sesión.
2. Esperar cinco minutos sin actividad y comprobar el cierre automático.
3. Crear, cambiar y liberar una IP de usuario y servidor.
4. Asignar un notebook y confirmar la IP sincronizada.
5. Revelar un secreto con reautenticación.
6. Revisar que los registros de auditoría no contengan claves ni tokens.

## 8. Respaldos y recuperación

- Respaldar MySQL diariamente y conservar al menos una copia fuera del servidor.
- Respaldar por separado el `.env` y `FIELD_ENCRYPTION_KEY` con acceso limitado.
- Probar periódicamente la restauración en una base aislada.
- Antes de cada despliegue: respaldar, ejecutar migraciones, validar el portal y
  conservar un procedimiento para volver al commit anterior.
- Confirmar y subir cada cambio significativo a `origin/main` después de pasar
  sus validaciones.
