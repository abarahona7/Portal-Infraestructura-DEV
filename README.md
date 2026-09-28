# Portal Infraestructura TI

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

## Desarrollo local

1. Crear y activar un entorno virtual Python.
2. Instalar `requirements.txt`.
3. Crear `.env` desde `.env.example` y generar una `FIELD_ENCRYPTION_KEY`
   estable. Django carga este archivo automáticamente y las variables definidas
   por el sistema tienen prioridad.
4. Ejecutar migraciones y `python manage.py runserver`.
5. En `siminfra-frontend`, instalar dependencias con `npm ci` y crear `.env.local` con:

```env
VITE_API_URL=/api
```

6. Ejecutar `npm run dev`.

No reutilizar una `FIELD_ENCRYPTION_KEY` distinta sobre una base que ya contenga secretos `ENC2::`; los secretos existentes solo pueden descifrarse con la clave con la que fueron cifrados.

## Producción

El perfil productivo es `config.settings_production`. Exige MySQL, desactiva
`DEBUG`, valida los secretos y rechaza cookies o HTTPS inseguros antes de
iniciar el portal.

Seguir [PRODUCTION_RUNBOOK.md](PRODUCTION_RUNBOOK.md) para preparar MySQL,
migrar los datos, compilar el frontend, validar el despliegue y configurar los
respaldos.

## Documentación técnica

- [Arquitectura y diagramas de flujo](docs/ARQUITECTURA_Y_FLUJOS.md)
- [Modelo de datos y relaciones](docs/MODELO_DATOS.md)
- [Migración verificada de SQLite a MySQL](docs/MIGRACION_MYSQL.md)

La entrega no incluye bases de datos, `.env` reales, claves, `node_modules`, `venv`, caches, backups ni `.git`.
