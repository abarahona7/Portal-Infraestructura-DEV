# Auditoría A04 y A02

Fecha de cierre: 23-10-2026.

## Alcance

Se revisaron el cifrado Fernet de campos, contraseñas Django, JWT, cookies,
tokens persistidos, transporte HTTP/MySQL, respaldos, WebSocket, configuración
de Django/DRF, Vite, Nginx, servicios y archivos de entrega. No se cambió la
clave Fernet real, no se recifraron datos y no se ejecutaron comandos de
saneamiento sobre DEV.

## Datos y claves sensibles

Los seis campos reversibles protegidos son las contraseñas Gmail/VPN del
usuario, PIN y contraseña iCloud del equipo, contraseña del perfil genérico y
contraseña del PC genérico. Serializers, exportaciones, Papelera, historiales y
WebSocket no entregan esos valores en claro. Los datos personales consultables
permanecen en columnas normales y dependen del cifrado y control de acceso de
MySQL, disco y respaldos.

`DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY` y las claves Fernet se validan y deben
ser distintas. MySQL y Redis reciben sus credenciales desde el entorno. No se
encontraron claves reales versionadas mediante la revisión heurística; esta no
reemplaza un escaneo especializado de secretos.

## Hallazgos corregidos

| Severidad | Hallazgo | Corrección |
| --- | --- | --- |
| Alta | `settings_production` podía heredar `DJANGO_ENV=development` | El módulo fuerza producción antes de importar la configuración y las pruebas demuestran que DEBUG/SQLite/cookies inseguras no pueden activarse |
| Alta | SimpleJWT persistía el contenido de refresh tokens | Los tokens nuevos se reemplazan por `redacted:jti:<jti>` conservando JTI, expiración y blacklist; existe saneamiento histórico con simulación por defecto |
| Alta | MySQL remoto podía iniciar sin CA | `DATABASE_SSL_CA` es obligatorio fuera de localhost, debe ser un archivo legible y activa `VERIFY_IDENTITY` |
| Media | No había rotación compatible de Fernet | `FIELD_ENCRYPTION_KEYS` habilita MultiFernet primario primero y el comando `rotate_secrets` simula por defecto, exige confirmación al aplicar y cubre registros archivados |
| Media | Un prefijo `ENC2::` falso podía persistirse desde la API | Los seis campos rechazan los prefijos criptográficos internos |
| Media | Un secreto corrupto producía error sin auditoría específica | Revelado falla cerrado con respuesta genérica y evento `DESCIFRADO_FALLIDO`, sin registrar el valor |
| Media | Hosts, orígenes, cookies, Redis y renderer tenían validación parcial | Producción rechaza host global, orígenes no HTTPS/comodín, cookie fuera de `/api/auth/`, Redis inválido y usa únicamente JSONRenderer |
| Media | El proxy carecía de CSP y cabeceras modernas | La plantilla agrega TLS 1.2/1.3, HSTS, CSP, frame deny, Permissions-Policy, COOP/CORP, referrer y oculta versión |
| Media | Respaldos y retención no tenían controles suficientes | El runbook exige cifrado separado, custodia de claves, restauración, política de retención y limpieza de tokens vencidos |

## Configuración operativa

| Variable | Cambio |
| --- | --- |
| `FIELD_ENCRYPTION_KEYS` | Nueva y opcional; claves Fernet separadas por comas, primario primero |
| `DATABASE_SSL_CA` | Obligatoria para MySQL remoto en producción |
| `DJANGO_ALLOWED_HOSTS` | No admite `*` en producción |
| `CORS_ALLOWED_ORIGINS` | Debe contener orígenes HTTPS explícitos |
| `CSRF_TRUSTED_ORIGINS` | Debe contener orígenes HTTPS explícitos |
| `JWT_COOKIE_PATH` | Debe ser `/api/auth/` |
| `JWT_COOKIE_SAMESITE` | Solo `Lax` o `Strict` |
| `USE_X_FORWARDED_PROTO` | Obligatorio en producción detrás del proxy documentado |

## Impacto

- Administrador, Operador y Visualizador conservan los mismos permisos y flujos.
- Un secreto corrupto ahora informa indisponibilidad de forma controlada en vez
  de responder con una excepción interna.
- No cambió el esquema ni se agregó una migración.
- Desplegar MultiFernet no modifica datos. La rotación solo ocurre al ejecutar
  el comando de aplicación con confirmación explícita.
- Los refresh vigentes siguen rotando y bloqueándose; solamente se minimiza su
  representación persistida.
- Producción deja de arrancar ante configuraciones que antes eran toleradas.

## Validación ejecutada

- Suite backend completa en SQLite temporal: 265 aprobadas, 3 omitidas.
- Pruebas nuevas de criptografía/tokens en MySQL 8.4 temporal: 11 aprobadas.
- Pruebas frontend: 69 aprobadas.
- Lint y build de producción frontend: aprobados.
- `manage.py check --deploy` con entorno productivo sintético: sin hallazgos.
- `git diff --check` y `manage.py check`: sin hallazgos.

## Acciones operativas pendientes

- No se ejecutó `sanear_tokens_refresh --apply` sobre DEV ni producción.
- No se ejecutó `rotate_secrets --apply` ni se cambió `FIELD_ENCRYPTION_KEY`.
- Aplicar `require_secure_transport=ON`, privilegios mínimos y firewall requiere
  intervención autorizada del administrador MySQL.
- Instalar la nueva plantilla Nginx y validar CSP/cabeceras requiere una ventana
  de QA y posterior recarga del proxy.
- Python, Django y MySQL deben actualizarse a sus parches soportados después de
  probar la actualización en QA. La auditoría completa de dependencias queda
  para la Parte 6.

## Hallazgos para otras partes

La definición formal de plazos de conservación y el análisis jurídico de datos
personales requieren aprobación organizacional. La revisión exhaustiva de CVE,
SBOM y dependencias transitivas no forma parte de A04/A02.
