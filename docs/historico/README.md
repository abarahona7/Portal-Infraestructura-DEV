# Documentación histórica

Esta carpeta conserva evidencia útil de trabajos ya completados sin llenar la
raíz del proyecto.

- `importacion/`: reglas y resultado de la importación inicial v1.1.
- `rendimiento/`: metodología, resultados y métricas antes/después de la
  optimización.

Los reportes con datos operacionales y los respaldos SQLite se guardan
localmente en `.local/`, que está excluida de Git. La base activa de desarrollo
continúa en `db.sqlite3` en la raíz porque esa es la ubicación predeterminada de
Django.
