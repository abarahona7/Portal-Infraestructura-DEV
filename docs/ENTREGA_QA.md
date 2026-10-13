# Preparar una entrega limpia para QA

El repositorio contiene aproximadamente 4 MB de archivos versionados. El
volumen visible en el servidor DEV corresponde sobre todo a `.venv/`,
`siminfra-frontend/node_modules/`, `siminfra-frontend/dist/` y `.local/`.
Son necesarios o útiles en DEV, pero no se transfieren como código fuente.
Tampoco se transfieren `.env`, `siminfra-frontend/.env.local`, bases de datos,
backups, logs, cachés ni `.git`.

## Fuente de la entrega

1. Revisar y probar el trabajo pendiente. `git status --short` debe quedar
   vacío después de registrar en Git los cambios aprobados. La entrega desde
   `HEAD` **no incluye modificaciones locales sin commit**.
2. Anotar `git rev-parse HEAD` y usar ese mismo commit para la entrega, la
   prueba en QA y cualquier despliegue posterior. No mezclar archivos de otra
   rama o de una copia local.
3. Desde la raíz del repositorio, crear el paquete con los archivos rastreados
   por Git:

```bash
git status --short
git rev-parse HEAD
install -d -m 700 .local/entregas
git archive --format=tar.gz --prefix=portal-qa/ --output=.local/entregas/portal-qa.tar.gz HEAD
tar -tzf .local/entregas/portal-qa.tar.gz | head
sha256sum .local/entregas/portal-qa.tar.gz
```

El paquete incluye `core/tests/`, migraciones, `requirements.txt`,
`package-lock.json`, configuración y documentación porque QA los necesita para
reproducir validaciones. Las pruebas y migraciones no son basura del proyecto.
El paquete **no lleva** las dependencias instaladas ni los datos locales, pues
no están rastreados por Git. Antes de enviarlo, comprobar que la lista del
archivo no contiene secretos o datos operacionales.

## Preparar el entorno QA

- Configurar una base MySQL 8.4 **independiente** de DEV y producción, con
  usuario y credenciales propios. No borrar ni recrear ninguna base existente
  para instalar el código; revisar `migrate --plan` y hacer respaldo cuando
  corresponda.
- Crear el `.env` de QA fuera del paquete a partir de
  `.env.production.example`, con `DJANGO_DEBUG=False`, dominio HTTPS de QA,
  secretos propios y `PORTAL_PUBLIC_URL` de QA. Si se copian datos cifrados
  desde DEV, la clave Fernet correspondiente debe transferirse por un canal
  seguro; con una clave distinta esos secretos no podrán descifrarse.
- Instalar dependencias con `python -m pip install -r requirements.txt` y
  `npm ci` en `siminfra-frontend/`. Construir el frontend con
  `VITE_API_URL=/api npm run build`. `dist/` se genera en QA; no se copia
  desde DEV.
- Ejecutar `manage.py check --deploy`, `manage.py migrate --plan`, las
  migraciones aprobadas, `manage.py migrate --check`,
  `manage.py validar_integridad_portal` y `manage.py collectstatic` usando
  `config.settings_production` y las variables de QA. Seguir el
  [runbook](../PRODUCTION_RUNBOOK.md) para HTTPS, proxy, WebSocket y pruebas
  funcionales. Las pruebas automatizadas que crean bases de prueba requieren
  una instancia aislada y permisos propios; nunca deben apuntar a DEV.

La entrega de código y la carga de datos son procesos distintos. Para probar
con datos reales, usar un respaldo restaurado en la base independiente de QA,
con acceso limitado y la clave de cifrado adecuada; no incluir el respaldo en
el archivo del código.
