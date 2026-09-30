# Continuidad del proyecto en el host de desarrollo

Actualizado el 29 de septiembre de 2026. Este documento resume el estado del
portal y el procedimiento para actualizar otro clon desde `origin/main`.

## Estado actual

### Arquitectura

- Backend: Django y Django REST Framework.
- Frontend: React 19, Vite y Axios.
- Desarrollo: SQLite. Producción: perfil preparado y validado para MySQL 8.
- Autenticación: access token JWT en memoria y refresh token en cookie HttpOnly.
- Sesión: renovación mediante refresh, protección CSRF y cierre tras cinco
  minutos de inactividad efectiva.
- Secretos: cifrado Fernet con `FIELD_ENCRYPTION_KEY` estable y revelado sujeto
  a rol, reautenticación y límite de solicitudes.
- Roles: Visualizador, Operador Infraestructura y Administrador.

### Funcionalidad consolidada

- Usuarios, Equipos por categoría, Gestión de IP, Anexos, Perfiles genéricos,
  Departamentos/Subáreas, PCs genéricos y Servidores.
- Asignaciones de IP centralizadas y sincronizadas para usuarios, servidores y
  PCs genéricos, con un único propietario válido.
- Sincronización de la IP del usuario en el notebook asociado.
- Historiales funcionales para los módulos principales y auditoría de acciones
  sensibles.
- Acta de entrega disponible solamente cuando el usuario posee al menos un
  equipo relacionado.
- Cambio a Licencia Médica libera solamente la IP. La baja libera IP, anexo y
  equipos después de la advertencia correspondiente.
- Interfaz responsiva, tablas contenidas, sidebar móvil, modales adaptables y
  controles táctiles.
- Paginación del backend, consultas relacionadas optimizadas y catálogos
  auxiliares cargados solo cuando la pantalla o formulario los necesita.
- Búsquedas con espera de 150 ms, cancelación de solicitudes obsoletas e
  indicador de actividad. Usuarios e IP admiten búsqueda global sin elegir
  previamente un área o segmento.

El detalle por módulo y los diagramas están en
[`ACCIONES_ACTUALES.md`](ACCIONES_ACTUALES.md),
[`ARQUITECTURA_Y_FLUJOS.md`](ARQUITECTURA_Y_FLUJOS.md) y
[`MODELO_DATOS.md`](MODELO_DATOS.md).

## Antes de actualizar el clon

El repositorio contiene código y migraciones. No contiene la base de datos,
archivos `.env`, claves, `venv`, `node_modules` ni datos operacionales.

1. Detener Django y Vite.
2. Respaldar fuera del repositorio la base utilizada por ese host y sus archivos
   `.env` y `siminfra-frontend/.env.local`.
3. Conservar la misma `FIELD_ENCRYPTION_KEY` de la base. Cambiarla impide
   descifrar los secretos que ya contiene.
4. Revisar que no existan cambios locales pendientes:

```powershell
git status --short
git branch --show-current
```

Si aparecen cambios en archivos versionados, confirmarlos en una rama o
guardarlos antes de actualizar. No sobrescribirlos con un reset.

## Traer la actualización desde GitHub

Ejecutar en la raíz del clon:

```powershell
git switch main
git fetch origin
git log --oneline HEAD..origin/main
git pull --ff-only origin main
git log -3 --oneline
```

`--ff-only` evita crear un merge accidental en el host. Si Git informa que no
puede avanzar de forma lineal, detenerse y revisar los commits o cambios locales
antes de continuar.

## Actualizar y validar el backend

Con el entorno virtual existente:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py validar_integridad_portal
```

`migrate` actualiza el esquema y conserva los registros. Aun así, el respaldo
previo es obligatorio para cualquier host que contenga datos relevantes.

## Actualizar y validar el frontend

```powershell
cd siminfra-frontend
npm ci
npm run lint
npm run build
cd ..
```

`npm ci` usa las versiones exactas de `package-lock.json`. El resultado del
build queda en `siminfra-frontend/dist`.

## Iniciar el perfil de desarrollo en red

Actualizar en `.env` la IP real del host en `DJANGO_ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS`. Mantener en
`siminfra-frontend/.env.local`:

```env
VITE_API_URL=/api
```

Terminal del backend, desde la raíz:

```powershell
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8008
```

Terminal del frontend:

```powershell
cd siminfra-frontend
npm run dev:lan
```

El navegador de otro equipo debe entrar a `http://IP_DEL_HOST:5176`. Las reglas
de firewall y el procedimiento completo están en
[`DESARROLLO_RED_LOCAL.md`](DESARROLLO_RED_LOCAL.md).

## Comprobación funcional posterior

1. Iniciar sesión y recargar la página; la sesión debe continuar.
2. Buscar un usuario por nombre sin seleccionar un área.
3. Buscar una IP sin seleccionar un segmento.
4. Abrir Agregar y Editar en Equipos y Anexos; el selector de usuario debe estar
   disponible.
5. Abrir formularios de Usuario, Servidor y PC genérico; los selectores de IP
   deben cargar y mantener las asignaciones sincronizadas.
6. Probar crear y editar con un registro de prueba y comprobar su historial.

## Datos entre ambos equipos

`git pull` actualiza el código, no los datos. Si el host debe usar la misma
información que otro equipo, se requiere un procedimiento separado de respaldo
y restauración de SQLite o de migración a MySQL. La base y la
`FIELD_ENCRYPTION_KEY` se deben trasladar por un canal seguro y nunca mediante
Git.

Para producción se debe seguir [`PRODUCTION_RUNBOOK.md`](../PRODUCTION_RUNBOOK.md)
y [`MIGRACION_MYSQL.md`](MIGRACION_MYSQL.md); `runserver` y `npm run dev:lan`
son herramientas de desarrollo.
