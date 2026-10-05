# Rendimiento actual del portal

Última medición: 29 de septiembre de 2026.

## Optimización del inicio de Usuarios

La vista de Usuarios utilizaba la lista auxiliar completa de usuarios para
calcular los conteos por departamento y el total del menú lateral. Esa carga se
reemplazó por la sección agregada `usuarios_stats`, que devuelve solamente el
total general y los conteos por departamento.

Mediciones locales con SQLite y cinco repeticiones:

| Indicador | Antes | Después | Variación |
| --- | ---: | ---: | ---: |
| Tiempo mediano del backend | 14,66 ms | 3,77 ms | -74,3 % |
| Tamaño de respuesta | 80.159 bytes | 6.610 bytes | -91,8 % |
| Consultas SQL | 3 | 3 | Sin cambio |

La lista auxiliar completa continúa disponible para los formularios de Equipos
y Anexos, donde se necesita para seleccionar o relacionar usuarios.

## Búsquedas interactivas y catálogos diferidos

Los buscadores de todos los módulos consultan el backend después de 150 ms sin
nuevas pulsaciones. Cuando el texto cambia, el frontend cancela la solicitud
anterior para evitar que una respuesta antigua sustituya el resultado más
reciente. El campo muestra un indicador mientras la consulta está pendiente.

Usuarios permite buscar en todas las áreas sin seleccionar previamente un
departamento. Gestión de IP permite buscar en todos los segmentos sin escoger
uno primero. Los filtros de departamento, segmento y estado continúan
combinándose con la búsqueda cuando están seleccionados.

La lista auxiliar completa de usuarios dejó de descargarse al entrar a Equipos
o Anexos. Se solicita una sola vez al abrir Agregar o Editar, se conserva en
memoria y se invalida cuando una modificación puede cambiar sus relaciones.
Esto elimina de la navegación de solo consulta una respuesta de 74.480 bytes y
una consulta SQL en Anexos; en Equipos evita la carga combinada de usuarios y
departamentos de 80.159 bytes y tres consultas SQL.

## Optimización de Departamentos y Subáreas

La pantalla ya obtiene su catálogo completo desde `/api/departamentos/`. Se
eliminó una segunda solicitud que descargaba nuevamente departamentos, usuarios
y perfiles sin utilizarlos.

| Indicador de la carga auxiliar eliminada | Antes | Después |
| --- | ---: | ---: |
| Solicitudes adicionales | 1 | 0 |
| Consultas SQL adicionales | 4 | 0 |
| Tiempo mediano adicional | 15,07 ms | 0 ms |
| Datos adicionales transferidos | 87.303 bytes | 0 bytes |

Después de modificar la estructura organizacional, los catálogos relacionados
se invalidan y se vuelven a solicitar solamente al entrar en Usuarios, Equipos,
Perfiles u otro módulo que realmente los necesita.

## Referencia de endpoints principales

| Endpoint | Mediana | Consultas SQL | Respuesta |
| --- | ---: | ---: | ---: |
| Usuarios | 9,58 ms | 3 | 44.979 bytes |
| Equipos | 4,47 ms | 2 | 19.374 bytes |
| IPs | 3,72 ms | 2 | 7.851 bytes |
| Anexos | 4,44 ms | 2 | 17.019 bytes |
| Perfiles genéricos | 3,97 ms | 2 | 15.208 bytes |
| PCs genéricos | 3,36 ms | 2 | 6.058 bytes |
| Servidores | 1,26 ms | 2 | 162 bytes |
| Departamentos | 3,44 ms | 2 | 5.662 bytes |

## Repetir la medición

```powershell
.\venv\Scripts\python.exe manage.py medir_rendimiento_portal --repeticiones 5
```

Los valores dependen del equipo, la base de datos y la carga del sistema. Para
comparaciones válidas se debe usar el mismo entorno y número de repeticiones.

## Sincronización entre usuarios

Equipos, Usuarios y los módulos relacionados siguen leyendo datos por la API
REST paginada. Después de confirmar una escritura, el backend envía por
WebSocket un evento con identificador, operación y módulos afectados. La
pestaña que está mostrando uno de esos módulos repite únicamente su consulta
visible; el tablero actualiza su resumen y, si hay una lista abierta, esa
lista. Los avisos cercanos se agrupan en el frontend y no se mantiene un
intervalo de consultas. La capa de canales en memoria sirve solo para un
proceso de desarrollo; producción requiere Redis compartido y Daphne.

El listado de Equipos utiliza `select_related` para usuario, IP y departamento
y cuenta con índice combinado `(tipo, estado)` para los filtros de categoría
y estado. No se agregaron campos ni migraciones para esta integración.
