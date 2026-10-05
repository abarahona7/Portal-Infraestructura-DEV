# Documentación histórica

Esta carpeta conserva evidencia útil de trabajos ya completados sin llenar la
raíz del proyecto.

- `importacion/`: reglas y resultado de la importación inicial v1.1.
- `rendimiento/`: metodología, resultados y métricas antes/después de la
  optimización.

Los reportes con datos operacionales y los respaldos de la base se guardan
localmente en `.local/`, que está excluida de Git. La base activa de DEV se
configura en `.env`; no forma parte del repositorio. Los respaldos previos a la
reconstrucción ITAM están comprimidos en
`.local/backups/historial_itam_20260929_20261001.tar.gz`; los respaldos de
reconstrucción y prueba de restauración permanecen como archivos SQL separados.
