# Verificación global de seguridad

Fecha de verificación: 23 de octubre de 2026  
Rama: `feature/itam-reinicio-limpio`  
Commit auditado: `3926ace2d1fac09faa0d181723d9bb85d8f41a87`

## Resumen ejecutivo

El portal tiene controles efectivos y pruebas automatizadas para autorización,
IDOR, autenticación, rate limiting, cifrado, inyección, SSRF, configuración
productiva, manejo de excepciones e integridad funcional. La suite SQLite, el
frontend y las pruebas transversales de abuso aprobaron.

La auditoría no aprueba todavía el paso a producción. Se comprobaron tres
bloqueos:

1. La suite completa ejecutada mediante `scripts/run_qa_mysql.py core` falla
   porque el runner no define una `JWT_SIGNING_KEY` independiente. El workflow
   de CI presenta la misma omisión.
2. `scripts/validar_proxy_publicacion.py` falla contra la plantilla Nginx
   vigente porque compara una cabecera HSTS antigua.
3. `npm audit` reporta dos dependencias vulnerables con severidad alta:
   `follow-redirects@1.16.0` y `vite@8.2.2`.

La cobertura A03 y A08 es parcial. Existen versiones Python fijadas,
`package-lock.json` con integridad, huellas SHA-256 para importaciones y reglas
de integridad de datos. No existe un control continuo de vulnerabilidades
Python, SBOM, procedencia firmada, firma de commits o artefactos, ni fijación
inmutable de acciones e imágenes por digest.

No se modificó código ni configuración durante esta revisión. Las pruebas
usaron bases temporales, salvo `validar_integridad_portal`, que consultó DEV en
modo de solo lectura y confirmó 23 reglas.

## Resultados de pruebas

| Verificación | Resultado | Observación |
| --- | --- | --- |
| Backend SQLite: `.venv/bin/python scripts/run_qa_sqlite.py core` | 277 aprobadas, 3 omitidas, 0 fallidas | Base SQLite temporal. |
| Backend MySQL: `.venv/bin/python scripts/run_qa_mysql.py core` | 276 aprobadas, 2 omitidas, 1 fallida | MySQL 8.4 temporal. Falla separación JWT/Django. |
| Prueba MySQL fallida con `JWT_SIGNING_KEY` sintética independiente | 1 aprobada | Confirma defecto del runner, no del rechazo productivo. |
| Frontend: `npm test -- --run` | 23 archivos, 70 pruebas aprobadas | Sin omisiones reportadas. |
| Abuso transversal | 48 aprobadas | Roles, IDOR, rate limit, secretos, inyección, SSRF y WebSocket. |
| Arranque productivo inseguro | 16 aprobadas | Configuraciones inseguras rechazadas. |
| `manage.py check --deploy` productivo | Ejecutado; 1 advertencia | `security.W021` por HSTS preload desactivado en el entorno sintético. El runbook documenta esta decisión. |
| Lint y build React | Aprobados | 1.988 módulos; build sin source maps públicos observados. |
| WebSocket aislado | Aprobado | REST, dos clientes, origen y autenticación. |
| Integridad funcional DEV, solo lectura | 23 reglas aprobadas | Sin incoherencias detectadas. |
| Proxy de producción | Fallido | El validador espera una cabecera HSTS anterior. |
| Proxy DEV oficina | Aprobado | HTTPS, QR, assets, API/admin e IP restringida. |
| `pip check` | Aprobado | No detectó requisitos rotos. |
| Auditoría Python de CVE | No ejecutada | `pip-audit` no está instalado. |
| `npm audit --json` | Fallido | 2 vulnerabilidades altas, 0 críticas. |
| Integridad Git: `git fsck --full --no-dangling` | Aprobada | Sin objetos dañados ni colgantes. |

### Pruebas omitidas

SQLite omitió tres pruebas que requieren bloqueos reales de MySQL:

- dos usuarios intentando reservar la misma IP;
- dos servidores intentando reservar la misma IP;
- dos IP simultáneas para el mismo propietario.

Estas pruebas se ejecutaron en la suite MySQL antes del fallo final y no
reportaron errores.

MySQL omitió dos pruebas deliberadamente específicas de SQLite:

- inyección de inconsistencias con `PRAGMA ignore_check_constraints`;
- simulación de una colisión heredada que la colación MySQL ya impide crear.

### Falla MySQL reproducida

La prueba
`TrustedProxyTests.test_jwt_declara_algoritmo_y_clave_independiente` exige que
la clave JWT sea distinta de `SECRET_KEY` y `FIELD_ENCRYPTION_KEY` en
`core/tests/test_auth_hardening.py:199-203`.

`scripts/run_qa_mysql.py:77-90` genera claves Django y Fernet, pero no define
`JWT_SIGNING_KEY`. En perfiles no productivos, `config/settings.py:365-366`
usa `SECRET_KEY` como fallback de JWT. Por eso la prueba falla.

El workflow presenta la misma contradicción en
`.github/workflows/validacion-portal.yml:29-53`: tampoco define
`DJANGO_SECRET_KEY` ni `JWT_SIGNING_KEY` independientes antes de ejecutar la
suite. La prueba aislada aprobó al suministrar una clave JWT sintética distinta.

## Pruebas de abuso por rol

| Actor | Abusos verificados | Resultado y evidencia |
| --- | --- | --- |
| Sin autenticar | Tablero, QR y API protegida | Rechazo `401`; `core/tests/test_qa_permissions.py:136-143`. |
| Visualizador | Otros módulos, anexo libre, observaciones, historial, POST, PATCH y DELETE | Otros módulos y escrituras rechazados; el anexo libre devuelve `404`; `core/tests/test_qa_permissions.py:42-87`. |
| Operador | DELETE, objetos inexistentes y revelado de secretos | DELETE y revelado rechazados `403`; `core/tests/test_qa_permissions.py:89-120`. |
| Administrador y superusuario | DELETE desde la API | Rechazado `403` y registro conservado; `core/tests/test_qa_permissions.py:122-134`. |
| Menor privilegio | Enumeración e IDOR por identificadores existentes e inexistentes | Querysets y permisos producen `403/404` sin acceso al objeto; suite transversal aprobada. |
| Login | Fuerza bruta por usuario e IP | `429`, `Retry-After` y auditoría; `core/tests/test_auth_hardening.py`. |
| Sesión | Refresh reutilizado, cambio de contraseña, desactivación y cambio de rol | Token anterior rechazado y sesiones revocadas; `core/tests/test_auth_hardening.py`. |
| Secretos | Revelado sin rol, sin contraseña válida, repetición y dato corrupto | Falla cerrada, throttle y auditoría; `core/tests/test_qa_security.py`. |
| Entrada hostil | SQL, lookups de relaciones, NUL, CRLF, prefijo criptográfico y secreto sobredimensionado | Payloads rechazados o tratados como parámetros; `core/tests/test_injection_security.py:97-156`. |
| SSRF | Loopback, metadata cloud y destino con DNS cambiante dentro de PDF | Se tratan como texto; ninguna URL se abre; `core/tests/test_injection_security.py:17-76`. |
| WebSocket | Origen ajeno, token inválido, mensaje grande, campos inesperados y abuso de frecuencia | Conexión cerrada con código controlado; `core/tests/test_auth_hardening.py` y `core/tests/test_realtime.py`. |

La API no expone una operación para cambiar grupos, `is_staff` o
`is_superuser`. La escalada mediante mass assignment no se observó en los
serializers operacionales. La gestión de cuentas Django permanece en el canal
administrativo.

## Revisión cruzada

### Rate limit y pruebas

El perfil de pruebas eleva los límites generales para evitar falsos positivos,
pero las pruebas de throttling aplican tasas pequeñas mediante overrides. Esto
mantiene la cobertura real. Redis falla cerrado mediante los throttles y el
WebSocket cierra con `1013`.

El diseño protege la seguridad, pero crea dependencia de disponibilidad: una
caída de Redis bloquea también API autenticada porque el throttle general no
puede comprobar su contador. Producción necesita Redis redundante y monitoreo.

### Validaciones y datos existentes

Las validaciones de serializers, transacciones, restricciones de base y
`validar_integridad_portal` son coherentes. La inspección de DEV confirmó 23
reglas. Las suites SQLite y MySQL aplicaron todas las migraciones hasta 0067.
No se detectó una validación nueva incompatible con los datos consultados.

### CSP y frontend

El build productivo aprobó. La CSP bloquea scripts inline y `eval`; mantiene
`'unsafe-inline'` solo en `style-src` porque existen estilos React inline. El
riesgo está documentado. `connect-src` contiene el dominio de ejemplo y debe
reemplazarse al instalar la plantilla.

La prueba automática del proxy no alcanzó todas sus verificaciones porque
`scripts/validar_proxy_publicacion.py:143,148,173` exige exactamente
`max-age=31536000`, mientras `deploy/nginx.portal.conf.example:25` agrega
`includeSubDomains; preload`. La plantilla es más estricta; la prueba está
desactualizada.

### Fail closed y disponibilidad

Permisos, reautenticación, auditoría de revelado, throttling y autenticación
WebSocket fallan cerrados. MySQL produce `503` genérico con `request_id` y una
falla de Channels no cambia datos ya confirmados por REST. El costo residual es
indisponibilidad ante fallas de Redis o del registro obligatorio de una
exportación.

### Criptografía y configuración

Producción exige claves Django, JWT y Fernet válidas e independientes, MySQL,
Redis compartido, cookies seguras, HTTPS, hosts y orígenes explícitos. Las 16
pruebas negativas aprobaron. La falla MySQL corresponde al entorno de QA/CI;
el perfil productivo sí rechaza la reutilización de claves.

## Matriz de cobertura

| Control | Estado | Evidencia verificada | Riesgo residual |
| --- | --- | --- | --- |
| A01 Broken Access Control | Cerrado | `core/permissions.py:18-58`; matriz por rol y 48 pruebas transversales. | Django Admin sigue siendo un canal privilegiado y requiere disciplina operativa. |
| A02 Security Misconfiguration | Parcial | `config/settings.py:110-138,308-347,448-482`; 16 pruebas negativas; `check --deploy`. | Validador Nginx productivo falla; dominio, TLS y cabeceras reales aún requieren QA externo. |
| A03 Software Supply Chain | Parcial | Versiones Python exactas; `package-lock.json` con hashes; CI con permisos `contents: read`. | Dos CVE altas npm; sin auditor Python, SBOM ni política automática; acciones e imagen MySQL usan tags mutables. |
| A04 Cryptographic Failures | Cerrado | Separación productiva de claves, MultiFernet y pruebas de secreto corrupto/oculto. | Custodia, rotación y recuperación de claves siguen siendo controles operativos. |
| A05 Injection | Cerrado | ORM, filtros explícitos, neutralización de fórmulas y pruebas SQL/CRLF/NUL/PDF. | Cualquier campo o exportación nueva debe reutilizar validadores existentes. |
| A06 Insecure Design | Parcial | Transacciones, concurrencia, reglas de negocio, modelo STRIDE y límites de volumen. | Sin doble aprobación para promoción a Administrador o retiros técnicos de alto impacto. |
| A07 Authentication Failures | Parcial | Rotación, blacklist, revocación, reautenticación y límites verificados. | Runner MySQL y CI violan el contrato de clave JWT independiente; MFA no está implementado. |
| A08 Software/Data Integrity | Parcial | Huellas SHA-256 de importación, `hmac.compare_digest`, locks npm, restricciones DB y 23 reglas. | Commits y artefactos sin firma; sin procedencia, SBOM o verificación inmutable de dependencias e imágenes. |
| A09 Exceptional Conditions/Logging | Parcial | Handler global, `request_id`, eventos estructurados, alertas y pruebas de fallos simulados. | No se verificó recolector externo, alerta real, retención ni almacenamiento append-only. |
| A10 SSRF | Cerrado | Guardia AST contra clientes salientes y payloads loopback/metadata/rebinding en PDF. | Toda conexión saliente futura debe pasar revisión; hoy no existe una función runtime dirigida por usuario. |
| IDOR | Cerrado | Permiso backend, `get_queryset`, `get_object` y pruebas de IDs existentes/inexistentes por rol. | El comportamiento debe repetirse al crear nuevos módulos o acciones custom. |
| Rate Limit | Cerrado | Login por IP/usuario, refresh, API, operaciones pesadas, secretos y WebSocket. | Redis es un punto de disponibilidad; no se verificó alta disponibilidad en el entorno final. |

“Cerrado” significa que no se encontró una brecha reproducible dentro del
alcance probado. No significa riesgo cero ni reemplaza QA con la topología
productiva real.

## Dependencias e integridad de entrega

- `pip check` no encontró conflictos, pero no busca CVE.
- `pip-audit` no está instalado. Las vulnerabilidades Python no quedaron
  verificadas contra una base de avisos.
- `npm audit` encontró:
  - `follow-redirects@1.16.0`: dos avisos altos relacionados con exposición de
    cabeceras sensibles en redirecciones (`GHSA-q3jh-wrc6-jgq8` y
    `GHSA-8r9p-f939-6h3c`);
  - `vite@8.2.2`: avisos del servidor de desarrollo, incluido uno alto
    (`GHSA-587h-7wmj-h5pm`). Vite no debe ejecutarse en producción, pero la
    dependencia vulnerable permanece en la cadena de desarrollo.
- `requirements.txt` fija versiones exactas, pero no contiene hashes de
  distribución.
- `package-lock.json` fija el tarball externo de SheetJS con SHA-512 en
  `siminfra-frontend/package-lock.json:2738-2741`.
- GitHub Actions usa `actions/checkout@v7` y `actions/setup-python@v7`, no SHA
  inmutables. MySQL usa `mysql:8.4`, no digest.
- El commit auditado no tiene firma criptográfica ni tag de liberación.
- `.gitignore` excluye `.env`, bases, respaldos locales, dependencias, builds y
  reportes con datos. `git fsck` aprobó.

## Revisión documental

| Documento | Estado | Diferencia encontrada |
| --- | --- | --- |
| `docs/ACCIONES_ACTUALES.md` | Consistente | Roles, Anexos asignados, DELETE bloqueado y exportación coinciden con código y pruebas. |
| `docs/ARQUITECTURA_Y_FLUJOS.md` | Consistente | Describe JWT, WebSocket, roles, límites y manejo de excepciones vigente. |
| `docs/MODELO_DATOS.md` | Parcial | Relaciones, cifrado y restricciones coinciden; no documenta el campo común `version` agregado por migración 0067. |
| `docs/MODELO_AMENAZAS.md` | Consistente con reservas | Registra doble aprobación, alertas externas, auditoría inmutable y MFA como pendientes. |
| `docs/ENTREGA_QA.md` | Consistente | Entrega por commit, exclusiones y separación de datos están alineadas. |
| `PRODUCTION_RUNBOOK.md` | Parcial | Conserva evidencia histórica de 176 pruebas; hoy son 277. Afirma que CI repite MySQL/proxy, pero ambos gates fallan con el código actual. |
| `.env.production.example` | Parcial | No incluye `PORTAL_EXPORT_MAX_ROWS` ni `PORTAL_WS_AUTH_TIMEOUT_SECONDS`, aunque el runbook los exige. Los defaults actuales son seguros. |
| A03/A08 | Pendiente documental | No existe una sección operativa de SBOM, auditoría de CVE, procedencia o firma de artefactos. |

## Riesgos residuales priorizados

### P0: resolver antes de producción

1. Corregir el runner MySQL y CI para generar claves Django, JWT y Fernet
   independientes. Repetir la suite completa y exigir resultado verde.
2. Alinear el validador Nginx con la cabecera HSTS vigente. Repetir ambas
   variantes del proxy en CI.
3. Actualizar `follow-redirects` y Vite a versiones corregidas. Ejecutar
   `npm ci`, lint, tests, build, proxy y `npm audit` hasta obtener cero riesgos
   altos o justificar formalmente cualquier excepción.

### P1: cerrar antes de la aprobación operativa

1. Incorporar auditoría Python de CVE, SBOM y una política de actualización.
2. Fijar acciones de CI e imágenes por SHA/digest aprobado.
3. Generar un artefacto de entrega con checksum, procedencia y firma. Registrar
   el commit exacto promovido a `main`.
4. Conectar `portal.security` a un recolector restringido y probar una alerta
   real. Definir retención y protección append-only.
5. Cifrar respaldos, separar las claves y demostrar una restauración en QA.
6. Actualizar documentación, cifras de pruebas, variables productivas y el
   campo de concurrencia `version`.

### P2: decisiones de diseño

1. Evaluar MFA para Administradores.
2. Definir doble aprobación para ascensos a Administrador y retiros técnicos
   de alto impacto.
3. Definir alta disponibilidad de Redis para equilibrar fail closed y
   continuidad operacional.
4. Aprobar una política para saltos mayores de Python, Django, Node, React,
   Vite y MySQL, con ensayo de rollback.
5. Aprobar retención y minimización para auditoría, historiales, papelera,
   respaldos y archivos de migración.

## Plan de mantenimiento

### En cada cambio

1. Ejecutar backend completo en SQLite y MySQL 8.4 aislado.
2. Ejecutar pruebas frontend, lint, build y validación de ambos proxies.
3. Ejecutar pruebas de abuso por rol y `check --deploy` con valores sintéticos.
4. Bloquear la integración si existe un fallo, una vulnerabilidad alta sin
   excepción o un cambio de esquema sin migración revisada.

### Mensualmente

1. Ejecutar auditores Python y npm con bases de avisos actualizadas.
2. Revisar versiones soportadas, imágenes y acciones de CI.
3. Regenerar SBOM y comparar dependencias agregadas o retiradas.
4. Revisar eventos `403`, `429`, fallos de login, revelados y errores `5xx`.

### Trimestralmente

1. Restaurar un respaldo cifrado en una red aislada y verificar secretos.
2. Ejecutar las 23 reglas de integridad y una prueba de recuperación completa.
3. Revisar matriz de roles, acciones custom, amenazas y riesgos aceptados.
4. Probar rotación de JWT, Django y Fernet en QA. No retirar una clave Fernet
   anterior hasta verificar que ningún dato la necesita.

### Antes de cada producción

1. Usar un commit aprobado, firmado y contenido en `main`.
2. Generar y verificar checksum y firma del paquete desplegado.
3. Ejecutar el checklist completo del runbook con el dominio, TLS, Redis,
   MySQL, proxy y recolector reales.
4. Registrar resultados, omisiones justificadas, responsables y rollback.

