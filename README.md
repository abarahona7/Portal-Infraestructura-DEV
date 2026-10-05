# Portal de Infraestructura TI Chile

Portal de gestión de usuarios, equipos, direcciones IP y recursos de Infraestructura.

## Stack

- Backend: Django REST Framework + Channels (HTTP y WebSocket mediante Daphne)
- Autenticación: JWT con access token en memoria y refresh token en cookie HttpOnly
- Frontend: React + Vite
- Base de datos: MySQL en DEV y producción; SQLite temporal para pruebas automatizadas
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
- Tablero de activos al abrir Equipos; ficha de equipo desde el listado

Los cambios se guardan mediante la API REST. El WebSocket avisa a las otras
sesiones qué módulos deben actualizar; no transmite datos del equipo ni
reemplaza las validaciones del backend.

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
4. Ejecutar migraciones y levantar el backend ASGI con
   `.venv/bin/daphne -b 127.0.0.1 -p 8005 config.asgi:application`.
5. En `siminfra-frontend`, instalar dependencias con `npm ci` y crear `.env.local` con:

```env
VITE_API_URL=/api
```

6. Ejecutar `npm run dev`. Abrir `http://127.0.0.1:5178`.

Para permitir pruebas desde otros equipos de la misma red, seguir
[Desarrollo en red local](docs/DESARROLLO_RED_LOCAL.md). El perfil LAN se
inicia con `npm run dev:lan` y mantiene la API detrás del proxy de Vite.

No reutilizar una `FIELD_ENCRYPTION_KEY` distinta sobre una base que ya contenga secretos `ENC2::`; los secretos existentes solo pueden descifrarse con la clave con la que fueron cifrados.

## Producción

El perfil productivo es `config.settings_production`. Exige MySQL, desactiva
`DEBUG`, valida los secretos y rechaza cookies o HTTPS inseguros antes de
iniciar el portal.

Seguir [PRODUCTION_RUNBOOK.md](PRODUCTION_RUNBOOK.md) para preparar MySQL,
migrar los datos, compilar el frontend, validar el despliegue y configurar los
respaldos.

## Documentación técnica

- [Mapa de acciones actuales por rol y módulo](docs/ACCIONES_ACTUALES.md)
- [Arquitectura y diagramas de flujo](docs/ARQUITECTURA_Y_FLUJOS.md)
- [Modelo de datos y relaciones](docs/MODELO_DATOS.md)
- [Migración verificada de SQLite a MySQL](docs/MIGRACION_MYSQL.md)
- [Desarrollo en red local](docs/DESARROLLO_RED_LOCAL.md)
- [Continuidad y actualización del host de desarrollo](docs/CONTINUIDAD_HOST_DESARROLLO.md)
- [Histórico de importación v1.1](docs/historico/importacion/IMPORTACION_V11.md)
- [Histórico de rendimiento v1.1](docs/historico/rendimiento/RENDIMIENTO_V11.md)

La entrega no incluye bases de datos, `.env` reales, claves, `node_modules`, `venv`, caches, backups ni `.git`.
