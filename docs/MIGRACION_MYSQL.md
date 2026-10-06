# Migración verificada de SQLite a MySQL 8.4

Este procedimiento mueve los datos existentes sin convertir manualmente el
archivo SQLite ni crear tablas a mano. Django crea el esquema MySQL desde sus
migraciones y carga una fixture portable.

## 1. Criterios de aceptación

La migración se considera válida cuando:

- todas las migraciones `core`, `auth` y `contenttypes` coinciden;
- los conteos de cada modelo coinciden;
- la huella SHA-256 ordenada de cada modelo coincide;
- las relaciones de grupos y permisos coinciden;
- `verify_secrets` confirma que los valores cifrados se pueden leer;
- pasan las comprobaciones de despliegue y las pruebas funcionales indicadas.

`PortalSession`, las sesiones Django y la lista de bloqueo JWT son datos
transitorios. Se excluyen y todos los operadores deben iniciar sesión nuevamente
después del cambio.

## 2. Preparación y respaldo

1. Definir una ventana sin escrituras y detener el backend.
2. Confirmar que el código desplegado corresponde a un commit respaldado.
3. Copiar `db.sqlite3` a un almacenamiento distinto del servidor.
4. Respaldar de forma segura `.env`, `FIELD_ENCRYPTION_KEY` y, si todavía se
   usa durante una transición, `LEGACY_DJANGO_SECRET_KEY`.
5. Verificar el origen antes de exportar:

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py migrate --check
.\venv\Scripts\python.exe manage.py validar_integridad_portal
.\venv\Scripts\python.exe manage.py verify_secrets
```

No continuar si alguno falla. En particular, cambiar `FIELD_ENCRYPTION_KEY`
haría ilegibles los secretos `ENC2::` existentes.

La migración `core.0059` recalcula los identificadores normalizados sin
acentos y agrega el ID de solicitud a la auditoría. Antes de aplicarla al
origen, ensayarla sobre una copia aislada: si dos registros pasan a tener la
misma clave, se detiene e informa sus ID sin fusionar ni borrar datos. Resolver
esa colisión con el responsable de los datos antes de continuar. El comando
`verify_secrets` ahora intenta descifrar cada valor `ENC2::` y falla si la
clave no corresponde; no muestra las contraseñas ni los valores descifrados.

## 3. Crear la auditoría del origen

```powershell
.\venv\Scripts\python.exe manage.py auditar_migracion_db --salida auditoria-sqlite.json
```

El archivo contiene conteos y hashes, no los valores originales. Se conserva
hasta terminar la validación del destino.

## 4. Exportar la fixture

```powershell
.\venv\Scripts\python.exe manage.py dumpdata `
  --natural-foreign `
  --natural-primary `
  --exclude contenttypes `
  --exclude auth.permission `
  --exclude admin.logentry `
  --exclude sessions.session `
  --exclude token_blacklist `
  --exclude core.portalsession `
  --indent 2 `
  --output portal-pre-mysql.json
```

La fixture contiene datos operacionales, hashes de contraseña y secretos
cifrados. Aunque no incluya secretos en texto legible, debe almacenarse con
acceso restringido y eliminarse del servidor al cerrar la migración.

Las señales del proyecto ignoran explícitamente las cargas con `raw=True`.
Esto evita que `loaddata` duplique historiales, libere recursos o ejecute otras
reglas laterales mientras reconstruye exactamente el estado exportado.

## 5. Preparar MySQL

Completar las variables de `.env.production.example` con valores reales. Para
el contenedor incluido:

```powershell
docker compose up -d db
docker compose ps
```

La configuración predeterminada publica MySQL solo en `127.0.0.1`, usa
`utf8mb4` y conserva los datos en el volumen `mysql_data`.

Comprobar la conexión con el perfil productivo:

```powershell
.\venv\Scripts\python.exe manage.py check --database default --settings=config.settings_production
```

## 6. Crear el esquema e importar

El destino debe estar vacío. No iniciar todavía el frontend ni el backend para
usuarios. Antes de ejecutar `loaddata`, comprobar y registrar que la base
destino no contiene datos operacionales. El comando `loaddata` del portal
rechaza una base con usuarios o registros de `core`, pero la revisión manual
del destino sigue siendo obligatoria. Nunca usar `loaddata` para actualizar
una base productiva existente.

```powershell
.\venv\Scripts\python.exe manage.py migrate --settings=config.settings_production
.\venv\Scripts\python.exe manage.py loaddata portal-pre-mysql.json --settings=config.settings_production
```

`migrate` crea tipos, índices, restricciones y permisos. `loaddata` inserta los
datos y restablece las secuencias de claves primarias.

## 7. Comparar origen y destino

```powershell
.\venv\Scripts\python.exe manage.py auditar_migracion_db `
  --salida auditoria-mysql.json `
  --comparar auditoria-sqlite.json `
  --settings=config.settings_production
.\venv\Scripts\python.exe manage.py validar_integridad_portal --settings=config.settings_production
```

El comando termina con error si cambia un conteo, una relación, una huella o el
conjunto de migraciones. No habilitar el portal si informa una diferencia.

Después validar cifrado y configuración:

```powershell
.\venv\Scripts\python.exe manage.py verify_secrets --settings=config.settings_production
.\venv\Scripts\python.exe manage.py check --deploy --settings=config.settings_production
.\venv\Scripts\python.exe manage.py migrate --check --settings=config.settings_production
```

## 8. Prueba funcional antes de abrir el acceso

1. Iniciar sesión con cada rol y recargar la página.
2. Consultar usuarios, equipos, IP, anexos, servidores, perfiles y PCs
   genéricos.
3. Verificar varios historiales antiguos y sus fechas.
4. Asignar y liberar una IP de prueba; confirmar ambas vistas e historiales.
5. Editar un usuario de prueba y confirmar los efectos de `LICENCIA` y `BAJA`.
6. Emitir un acta con equipos y comprobar el mensaje al intentar emitirla sin
   equipos.
7. Revelar un secreto con reautenticación y revisar el evento de seguridad.
8. Confirmar que no aparezcan errores de restricciones, codificación o zona
   horaria en los logs.

## 9. Habilitación y limpieza

1. Conservar el respaldo SQLite intacto.
2. Iniciar el backend productivo y publicar el frontend compilado.
3. Habilitar el acceso y observar errores y tiempos de respuesta.
4. Guardar `auditoria-sqlite.json` y `auditoria-mysql.json` junto al acta de la
   migración.
5. Eliminar `portal-pre-mysql.json` del servidor cuando el respaldo definitivo
   de MySQL esté probado.

## 10. Vuelta atrás

Si una validación falla antes de habilitar el portal, detener MySQL, conservarlo
para diagnóstico y volver a iniciar el commit anterior con la copia de SQLite y
su `.env`. Si ya hubo escrituras en MySQL, no alternar bases ni copiar registros
manualmente: cerrar el acceso, respaldar ambas bases y definir una reconciliación
controlada para no perder cambios.

Después de la estabilización, los respaldos habituales deben realizarse con las
herramientas de MySQL y probarse periódicamente en una instancia aislada.
