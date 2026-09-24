# Optimización de rendimiento v1.1

Fecha de validación: 23-09-2026.

## Metodología

Las mediciones se realizaron contra la base de datos local actual mediante el
comando `medir_rendimiento_portal`. Cada endpoint se ejecutó tres veces y se
registró la mediana del tiempo, la cantidad de consultas SQL y el tamaño de la
respuesta. Los archivos con las muestras completas son:

- `rendimiento_antes_v11.json`
- `rendimiento_despues_v11.json`

Comando para repetir la medición:

```powershell
.\venv\Scripts\python.exe manage.py medir_rendimiento_portal --repeticiones 3 --salida rendimiento_actual_v11.json
```

## Resultados de API y base de datos

| Endpoint | Tiempo antes | Tiempo después | Consultas antes | Consultas después | Respuesta antes | Respuesta después |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Usuarios | 541,10 ms | 59,33 ms | 1.584 | 2 | 410.134 B | 293.571 B |
| Equipos | 156,77 ms | 13,79 ms | 366 | 1 | 256.081 B | 147.628 B |
| IPs | 22,89 ms | 23,22 ms | 2 | 1 | 202.962 B | 202.962 B |
| Anexos | 88,62 ms | 9,02 ms | 201 | 1 | 104.668 B | 54.267 B |
| Perfiles genéricos | 3,26 ms | 3,80 ms | 1 | 1 | 16.767 B | 16.767 B |
| PCs genéricos | 5,14 ms | 1,53 ms | 2 | 1 | 7.258 B | 4.818 B |
| Servidores | 0,63 ms | 0,94 ms | 1 | 1 | 2 B | 2 B |
| Departamentos | 3,04 ms | 3,21 ms | 2 | 2 | 5.662 B | 5.662 B |

Las variaciones menores a un milisegundo en endpoints pequeños corresponden al
ruido normal de una ejecución local. No aumentó su cantidad de consultas ni el
tamaño de respuesta.

## Segunda fase: paginación y carga parcial

Fecha de validación: 24-09-2026.

Los listados operativos ahora entregan 50 registros por página y aceptan hasta
200 registros por solicitud. La medición se repitió con la misma base local y
tres muestras por endpoint:

| Endpoint | Tiempo sin paginación | Tiempo paginado | Respuesta sin paginación | Respuesta paginada |
| --- | ---: | ---: | ---: | ---: |
| Usuarios | 59,33 ms | 10,62 ms | 293.571 B | 44.952 B |
| Equipos | 13,79 ms | 4,33 ms | 147.628 B | 19.374 B |
| IPs | 23,22 ms | 3,00 ms | 202.962 B | 5.763 B |
| Anexos | 9,02 ms | 5,29 ms | 54.267 B | 17.019 B |
| Perfiles genéricos | 3,80 ms | 4,29 ms | 16.767 B | 15.208 B |
| PCs genéricos | 1,53 ms | 2,10 ms | 4.818 B | 4.909 B |
| Servidores | 0,94 ms | 1,22 ms | 2 B | 92 B |

En los listados grandes, Usuarios redujo su respuesta un 84,7 %, Equipos un
86,9 %, IPs un 97,2 % y Anexos un 68,6 %. Cada listado paginado agrega una
consulta `COUNT` constante para informar el total de resultados. En los
listados pequeños, la envoltura de paginación puede agregar algunos bytes y una
variación inferior a un milisegundo.

La interfaz aplica los filtros, la búsqueda y el ordenamiento desde el backend.
Usuarios se consulta después de seleccionar un departamento y las IP después de
seleccionar un segmento. La búsqueda espera 300 ms desde la última pulsación y
las exportaciones recorren todas las páginas para mantener el archivo completo.
Los contadores de segmentos IP se obtienen mediante un resumen y ya no requieren
descargar todos los registros para dibujar las tarjetas.

Los límites se pueden configurar mediante `PORTAL_PAGE_SIZE` y
`PORTAL_MAX_PAGE_SIZE`.

Mejoras principales:

- Usuarios: 89,0 % menos tiempo y 99,9 % menos consultas.
- Equipos: 91,2 % menos tiempo y 99,7 % menos consultas.
- Anexos: 89,8 % menos tiempo y 99,5 % menos consultas.
- El endpoint unificado `/api/reference-data/` entrega usuarios, IPs,
  departamentos y perfiles de referencia en una sola solicitud, con 5
  consultas, 25,78 ms y 226.183 B.
- La carga inicial del módulo Usuarios solicita solo usuarios y departamentos:
  3 consultas, 13,53 ms y 80.139 B. Frente a la carga inicial anterior, baja de
  4 solicitudes y aproximadamente 635,5 kB a 1 solicitud y 80,1 kB.

## Cambios realizados

### Backend y API

- Se eliminaron los N+1 mediante `select_related` y `prefetch_related`.
- Los listados usan serializadores reducidos y ya no incluyen historiales ni
  campos que solo se necesitan al editar o ver el detalle.
- Los historiales y relaciones completas se cargan al abrir una ficha o el
  historial de un registro.
- Se agregó un endpoint unificado y parcial para datos de referencia. El
  parámetro `include` permite solicitar solo las secciones necesarias.
- Se agregaron índices compuestos para los filtros y ordenamientos frecuentes
  de usuarios, anexos, IPs, equipos y perfiles.
- Se agregó una prueba automática que limita la cantidad de consultas de los
  listados principales y valida la respuesta reducida.

### Frontend

- Las solicitudes simultáneas idénticas se reutilizan, lo que evita duplicados
  durante renderizados concurrentes y durante el modo estricto de desarrollo.
- Los datos de referencia permanecen en el estado de la aplicación y solo se
  actualizan las secciones afectadas por cada modificación.
- Cada módulo solicita únicamente los catálogos que utiliza. El catálogo de IPs
  se carga de forma diferida cuando se abre un formulario de usuario o servidor.
- La aplicación dejó de volver a solicitar todos los catálogos después de cada
  alta, edición o eliminación.
- Los detalles e historiales se solicitan cuando el usuario los abre.
- La librería XLSX se carga únicamente al exportar un archivo. El JavaScript
  inicial de producción bajó de 709,92 kB a 430,29 kB y su tamaño gzip bajó de
  212,00 kB a 118,48 kB.
- Los listados usan paginación del servidor; al cambiar página solo se solicita
  el bloque visible y las exportaciones siguen incluyendo todos los registros.
- Los filtros de equipos, estados y segmentos IP se resuelven en la API para
  que los totales y las páginas sean coherentes con la selección activa.

### Estrategia de caché

Se utiliza caché en memoria durante la sesión para los datos de referencia y
deduplicación de solicitudes en curso. No se agregó una caché prolongada en el
backend porque usuarios, asignaciones de IP y equipos son datos operativos; una
caché sin invalidación inmediata podría mostrar disponibilidad incorrecta.

## Validaciones

- 67 pruebas de Django disponibles: 66 aprobadas y 1 prueba de concurrencia
  omitida en SQLite porque requiere los bloqueos reales de MySQL.
- `python manage.py check` sin observaciones.
- Lint del frontend sin errores.
- `npm run build` completado correctamente.
- `npm run start -- --host 127.0.0.1 --port 4173` respondió HTTP 200 y sirvió el
  elemento raíz de la aplicación.
- Migración `0040_anexo_idx_anexo_estado_num_and_more` aplicada.
- Respaldo anterior a los índices:
  `db.sqlite3.pre_optimizacion_20260923_165840.bak`.
