# Despliegue de producción

Este procedimiento publica el portal con MySQL 8.4, HTTPS y el perfil
`config.settings_production`. Los secretos reales se guardan únicamente en el
`.env` del servidor y nunca se agregan a Git.

Estado actual de la reconstrucción: las migraciones hasta `core.0060` y las
pruebas funcionales se validaron en MySQL **DEV**. Antes de aplicar 0059/0060 se
restauró un respaldo nuevo en MySQL 8.4 aislado y se verificaron conteos y QR;
el resultado está en [la guía de actualización](docs/ACTUALIZACION_MYSQL_84.md).
QA y producción necesitan sus propias bases,
accesos y respaldos; no se debe apuntar un despliegue productivo a
`portalinfra_dev`. Antes de liberar, confirmar con Infraestructura la URL HTTPS
definitiva, el proxy, la base de QA/producción y la ventana de despliegue.
Las decisiones y comprobaciones aún abiertas se registran en
[la revisión de ambigüedades](docs/REVISION_AMBIGUEDADES_PRODUCCION.md).

Verificación técnica de la versión actual (7 de octubre de 2026): **176 pruebas
de `core` ejecutadas en MySQL 8.4 temporal, sin fallos (2 omisiones)**. La base
y el contenedor se retiraron al terminar. La misma suite pasó también en SQLite
temporal: **176 pruebas, sin fallos y 3 omisiones**. El ejemplo Nginx
pasó una prueba aislada de sintaxis, HTTPS, carga directa de QR,
archivos, estáticos y proxy de API/admin. Esta evidencia aún no reemplaza la
prueba funcional en QA ni la revisión del entorno productivo definitivo. La
suite incluye la migración 0060, el bloqueo del borrado de IP asignada y la
protección de `loaddata` sobre bases con datos operacionales.
También se restauró un respaldo de DEV en MySQL 8 aislado: los 365 equipos
conservaron sus ID y QR y no faltaron migraciones. En el DEV actual, las nuevas
reglas de integridad detectan dos números móviles compartidos entre cuatro
equipos asignados a personas distintas (IDs 44, 93, 101 y 204). Es necesario
confirmar la titularidad y conciliar estos registros antes de exigir que la
validación de integridad vuelva a pasar; no se modificaron automáticamente.

Para habilitar QA se deben confirmar la base MySQL independiente y los permisos
para aplicar migraciones, la URL y el certificado HTTPS propios, `PORTAL_PUBLIC_URL`
apuntando a esa URL, acceso al servidor y una cuenta con rol de prueba. En QA
se debe ejecutar la sección 4 y completar la sección 7 antes de proponer una
fecha de producción.

## 1. Preparar el servidor

1. Instalar Python, las dependencias de `requirements.txt`, Node.js y MySQL 8.4.
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

**Si `mysql_data` ya contiene una base MySQL 8.0, no ejecutar `docker compose
up` todavía.** El cambio de imagen a 8.4 puede actualizar ese volumen. Antes,
obtener un respaldo verificable, ensayar la restauración en una instancia
aislada y acordar una ventana de mantenimiento. Consultar
[la guía de actualización](docs/ACTUALIZACION_MYSQL_84.md). Si la base está
administrada fuera de Docker, no reiniciar ni recrear un contenedor local.

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

En una instancia MySQL aislada para pruebas, ejecutar la suite completa:

```powershell
.\venv\Scripts\python.exe manage.py test core --settings=config.settings_production
```

La suite incluye rollback con fallos inyectados, dos asignaciones simultáneas
sobre una misma IP y el flujo de sesión/QR bajo HTTPS. Usar solo una instancia
aislada con permiso para crear y eliminar la base de pruebas; no apuntar este
comando a DEV compartido ni a producción.

## 3. Preparar los datos de producción

Si la instalación productiva comienza con una base MySQL nueva, crear una base
separada y ejecutar únicamente `migrate` sobre ella. Si ya existe una base
productiva, respaldarla y revisar `migrate --plan` antes de aplicar cambios;
no ejecutar `loaddata` sobre datos existentes. Los pasos siguientes de esta
sección aplican **solo** a una instalación que todavía migra desde SQLite.
El comando `loaddata` del portal rechaza bases con usuarios o registros de
`core`; antes de una importación, verificar igualmente que el destino es el
correcto y registrar la comprobación de vacío.

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

4. Activar el `.env` productivo, comprobar y registrar que el destino no tiene
   datos operacionales, y solo entonces crear el esquema e importar:

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

El proxy HTTPS debe servir `dist`, enviar `/api` y `/ws/` al backend y servir
`staticfiles` como contenido estático. Mantener frontend y API bajo el mismo
origen permite que Axios envíe el token CSRF sin exponerlo a otros dominios.
En Linux, después de compilar, ejecutar
`python3 scripts/validar_proxy_publicacion.py`: levanta un Nginx temporal en
puertos locales y comprueba HTTPS, assets, `/api` y la ruta QR sin tocar el
servicio activo ni la base de datos.
Antes de publicar, ejecutar además
`.venv/bin/python scripts/verify_realtime_sqlite.py`: crea una base temporal,
edita un equipo por REST y verifica que dos clientes WebSocket reciben un solo
aviso y que un origen ajeno no puede conectarse.
También debe entregar `dist/index.html` para rutas del frontend como
`/qr/a/<uuid>`; de lo contrario, el código QR abrirá una página 404 al
escanearlo. Definir `PORTAL_PUBLIC_URL` con la URL HTTPS real del frontend,
sin ruta final. El perfil productivo rechaza una URL HTTP o mal formada.
El flujo de GitHub Actions repite la suite de MySQL, la prueba aislada de
WebSocket y ambas variantes del proxy en cada cambio de la rama de trabajo y
de `main`; la comprobación en QA con el dominio real sigue siendo obligatoria.
El ejemplo [deploy/nginx.portal.conf.example](deploy/nginx.portal.conf.example)
incluye las rutas necesarias; reemplazar dominio, directorios y certificados
antes de instalarlo. Validar la configuración con `nginx -t` antes de recargar
el servicio, sin modificar los otros sitios del host. Tras publicarlo, abrir
directamente `https://<dominio>/qr/a/<uuid>` en una ventana nueva: debe cargar
el frontend y pedir autenticación, no devolver 404. Comprobar además que
`/api/auth/me/` llega a Django y que el puerto interno 8000 no es público.

## 6. Ejecutar el backend

Configurar `PORTAL_CHANNEL_REDIS_URL` con una instancia Redis privada antes de
arrancar. El perfil productivo rechaza su ausencia; Redis permite compartir
eventos entre procesos ASGI. No publicar Redis a los navegadores.

No utilizar `runserver` en producción. Daphne sirve HTTP y WebSockets desde
la misma aplicación ASGI; debe escuchar solamente en la interfaz del proxy:

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings_production'
.\venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 config.asgi:application
```

En Linux, el comando equivalente es:

```bash
DJANGO_SETTINGS_MODULE=config.settings_production .venv/bin/daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

El proxy debe reemplazar `X-Forwarded-Proto` y evitar que el cliente se conecte
directamente a Daphne. `/ws/` debe admitir el upgrade de WebSocket. Solo después de confirmar HTTPS en todo el sitio se
debe habilitar HSTS.

En producción los logs se escriben como JSON en la salida estándar. Cada
respuesta incluye `X-Request-ID`, y el mismo valor aparece en los logs internos
del ciclo de esa solicitud. El recolector de logs debe conservar este campo y
restringir el acceso a los registros.

## 7. Verificación funcional

1. Iniciar sesión y recargar la página sin perder la sesión.
2. Esperar cinco minutos sin actividad y comprobar el cierre automático.
3. Crear, cambiar y liberar una IP de usuario; crear y cambiar la IP de un
   servidor de prueba, y confirmar que al eliminar ese servidor se libera.
4. Asignar un notebook y confirmar la IP sincronizada.
   Con otra sesión abierta en el listado, confirmar que la ficha y el listado
   muestran el cambio sin F5. Cortar y restablecer la red para comprobar la
   reconexión, y verificar que cerrar sesión detiene los avisos.
5. Revelar un secreto con reautenticación.
6. Revisar que los registros de auditoría no contengan claves ni tokens.
7. Abrir el tablero de activos y comprobar que cada pendiente lleva a los
   mismos equipos que cuenta el resumen; abrir también un departamento.
8. Escanear físicamente, desde un dispositivo real, un QR de un equipo asignado
   y otro sin usuario: la ficha debe requerir sesión, mostrar el departamento
   correcto o «Sin departamento asignado» y conservar el mismo QR tras una
   edición. Probar acceso directo
   con los roles Operador, Administrador y Visualizador.
9. Descargar el acta tradicional, abrir el PDF y revisar visualmente su diseño
   y el espacio de RUT manuscrito.
10. Exportar Excel desde los módulos disponibles y abrir los archivos en una
    hoja de cálculo; revisar encabezados, filas y caracteres especiales.
11. Probar el dominio y certificado HTTPS reales con un navegador externo al
    servidor. Verificar el proxy, el inicio de sesión, `/api` y la carga directa
    de `/qr/a/<uuid>`; comprobar que el backend interno no sea accesible
    directamente.
12. Probar una baja y reactivación de usuario: confirmar qué sucede con IP,
    anexo y equipos, incluido el posible re-enlace por hostname de Notebook/Mac.
13. Resolver las puertas de salida de la revisión de ambigüedades y confirmar
    las mismas operaciones en QA antes de programar producción.

## 8. Respaldos y recuperación

- Respaldar MySQL diariamente y conservar al menos una copia fuera del servidor.
- Respaldar por separado el `.env` y `FIELD_ENCRYPTION_KEY` con acceso limitado.
- Probar periódicamente la restauración en una base aislada.
- Antes de cada despliegue: respaldar, ejecutar migraciones, validar el portal y
  conservar un procedimiento para volver al commit anterior.
- La reconstrucción se trabaja actualmente en `feature/itam-reinicio-limpio`.
  Después de QA y revisión de los cambios locales pendientes, integrar el
  commit aprobado en `main` y verificar `origin/main` antes de desplegarlo.
  No asumir que la rama de trabajo ya está incluida en producción.
