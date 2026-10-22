# Auditoría A05 y A10

Fecha de cierre: 22-10-2026.

## Alcance e inventario de entradas

Se revisaron las rutas REST de usuarios, equipamiento, IP, anexos, servidores,
perfiles genéricos y PCs genéricos, incluidas sus acciones personalizadas. Las
entradas alcanzan parámetros de ruta por ID o UUID, búsqueda, filtros,
ordenamiento y paginación, cuerpos JSON procesados por serializers, cabeceras de
autenticación, cookies y nombres usados en respuestas descargables.

También se revisaron los formularios React que alimentan esas rutas, los datos
exportados a XLSX, el primer mensaje JSON del WebSocket y los libros locales que
procesan `importar_datos_v11` y `asignar_equipos_usuarios`. El portal no expone
una carga web de estos libros: su entrada corresponde a comandos internos.

## Sumideros y trazabilidad

- La consulta de datos usa ORM, con campos de búsqueda, filtro y ordenamiento
  declarados. No se encontró SQL crudo construido con entrada del cliente.
- No se encontraron `shell=True`, `os.system`, `eval`, `exec`, `pickle`,
  `yaml.load` inseguro ni plantillas construidas desde texto del usuario en el
  runtime del portal.
- El PDF del acta entrega datos persistidos a `Paragraph` de ReportLab. Antes de
  esta corrección, una etiqueta `img` podía hacer que ReportLab intentara leer
  un archivo o URL indicado por el dato. Ahora esos valores se escapan y se
  convierten en texto literal antes del render.
- Las exportaciones usan SheetJS y crean celdas de tipo texto. Las pruebas
  confirman que valores iniciados con `=`, `+`, `-` o `@` no se convierten en
  fórmulas.
- Las importaciones usan `openpyxl` con `read_only=True` y `data_only=True`.
  Ahora validan el archivo y la estructura ZIP antes de abrir el libro.
- No existe una función del servidor que acepte del usuario un destino para una
  conexión saliente. Una prueba estática falla si se incorpora un cliente HTTP
  o socket nuevo en el runtime sin revisión y centralización previa.

## Hallazgos corregidos

| Severidad | Hallazgo | Corrección |
| --- | --- | --- |
| Alta | Marcado ReportLab controlado por datos podía provocar lectura local o una solicitud saliente | Escapado obligatorio de nombres, áreas, equipos, series, activos, estados y firmas antes de crear cada `Paragraph` |
| Media | Un secreto demasiado largo podía superar la columna luego de cifrarse con Fernet | Límite previo al cifrado de 127 bytes UTF-8, sin modificar secretos existentes |
| Media | El WebSocket no limitaba el tamaño total del mensaje y toleraba campos extra durante autenticación | Límite configurable de 16 KiB, rechazo de frames binarios y esquema inicial exacto `type`/`token` |
| Baja | Textos podían contener NUL u otros controles invisibles | Validación común de textos recibidos por serializers; se conservan tabulación y salto de línea |
| Baja | Los XLSX se abrían sin límites estructurales previos | Validación de firma ZIP, archivo regular, symlink, rutas internas, cifrado, tamaño, miembros, filas y columnas |
| Baja | El nombre del PDF se interpolaba manualmente en `Content-Disposition` | Uso del generador seguro de cabeceras de Django |

## Evidencia conservada

- Los filtros y búsquedas continúan usando el ORM y payloads sintéticos con
  comillas o `UNION` se tratan como datos.
- React conserva su escapado predeterminado y no se introdujo render de HTML.
- El WebSocket solo comunica avisos de módulos y no incorpora datos de negocio.
- Las importaciones mantienen su previsualización, huella SHA-256 y aplicación
  transaccional.
- No cambiaron endpoints, modelos, migraciones, permisos ni roles.

## Impacto por rol y datos existentes

Administrador, Operador y Visualizador mantienen las mismas funciones y
permisos. Los controles son comunes al endpoint correspondiente y no conceden
capacidades nuevas. Los registros existentes no se reescriben ni se vuelven a
cifrar; el límite de secretos y el rechazo de caracteres de control se aplican
solo al crear o modificar valores.

## Límites configurables

| Variable | Valor predeterminado |
| --- | ---: |
| `PORTAL_WS_MAX_MESSAGE_BYTES` | 16384 bytes |
| `PORTAL_IMPORT_MAX_FILE_BYTES` | 26214400 bytes |
| `PORTAL_IMPORT_MAX_UNCOMPRESSED_BYTES` | 104857600 bytes |
| `PORTAL_IMPORT_MAX_ZIP_MEMBERS` | 10000 |
| `PORTAL_IMPORT_MAX_ROWS` | 50000 por hoja |
| `PORTAL_IMPORT_MAX_COLUMNS` | 100 por hoja |

## Validación ejecutada

- Suite backend SQLite: 248 pruebas aprobadas, 3 omitidas.
- Regresión focalizada SQLite: 34 pruebas aprobadas.
- Regresión focalizada MySQL 8.4: 15 pruebas aprobadas.
- Frontend: 69 pruebas aprobadas y build de producción correcto.

## Hallazgos para otras partes

No se corrigieron categorías OWASP fuera de A05/A10. La política de cabeceras
del navegador, dependencias, configuración criptográfica y monitoreo operativo
deben revisarse en las etapas que les correspondan.
