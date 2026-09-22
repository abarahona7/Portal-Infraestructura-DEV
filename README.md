# Portal Infra v1.0.0

Versión funcional definitiva del Portal Infraestructura TI.

## Stack

- Backend: Django + Django REST Framework
- Autenticación: JWT con access token en memoria y refresh token en cookie HttpOnly
- Frontend: React + Vite
- Base de datos: SQLite para desarrollo; MySQL preparado para producción
- Cifrado: Fernet para campos sensibles (`ENC2::`)
- UI: Inter + Lucide React

## Módulos

- Usuarios
- Equipamiento
- IPs
- Anexos
- Servidores
- Perfiles Genéricos
- PCs Genéricos

## Roles

- `Visualizador`: acceso únicamente a Anexos, solo lectura.
- `Operador Infraestructura`: lectura, creación, edición y asignación; no elimina ni revela secretos.
- `Administrador`: acceso completo y revelado de secretos tras reautenticación.
- Superuser: tratado como Administrador.

## Estado funcional congelado

La versión `v1.0.0` congela el alcance funcional. A partir de esta versión se recomienda aceptar solo:

- corrección de errores;
- mejoras de seguridad;
- ajustes visuales/responsive que no cambien el comportamiento;
- mantenimiento de dependencias y compatibilidad de infraestructura.

## Desarrollo local

1. Crear y activar un entorno virtual Python.
2. Instalar `requirements.txt`.
3. Configurar las variables locales requeridas, especialmente una `FIELD_ENCRYPTION_KEY` estable.
4. Ejecutar migraciones y `python manage.py runserver`.
5. En `siminfra-frontend`, instalar dependencias con `npm ci` y crear `.env.local` con:

```env
VITE_API_URL=http://127.0.0.1:8000/api
```

6. Ejecutar `npm run dev`.

No reutilizar una `FIELD_ENCRYPTION_KEY` distinta sobre una base que ya contenga secretos `ENC2::`; los secretos existentes solo pueden descifrarse con la clave con la que fueron cifrados.

## Producción

Revisar antes de desplegar:

- `PRODUCTION_CHECKLIST.md`
- `SECURITY_CHANGES.md`
- `MIGRATION_SECURITY.md`
- `TEST_RESULTS.md`
- `RELEASE_NOTES_v1.0.0.md`

La entrega no incluye bases de datos, `.env` reales, claves, `node_modules`, `venv`, caches, backups ni `.git`.
