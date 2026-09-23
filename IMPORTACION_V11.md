# Importación v1.1: revisión previa

El comando `importar_datos_v11` procesa los cinco Excel de `Portal SimInfra/IMPORTAR`. No modifica registros ya existentes: las filas que coinciden con registros o contienen claves ambiguas se reportan para revisión.

## Reglas acordadas

- `Departamento/Área` se carga como Departamento. La Subárea queda vacía para completarla en el portal.
- Todos los equipos nuevos quedan sin usuario y en `STOCK`. El [CSV de equipos sin usuario](equipos_sin_usuario_v11.csv) indica hoja, fila, tipo, marca, modelo, serie y activo fijo para el enroque manual.
- Las IP nuevas se crean únicamente con su dirección, en `LIBRE`, sin usuario, `asignado_otro` ni observación. Por ello, las direcciones que el Excel describe como ocupadas también aparecerán libres hasta que se revisen en el portal.
- Los anexos se asignan solo cuando nombre y correo disponibles identifican exactamente a un usuario único. Los demás se crean sin usuario.
- A los nombres de cuenta Gmail sin `@` se les añade `@gmail.com`.
- Los perfiles sin tipo explícito usan `On Premise`.
- La contraseña de red de la columna 6 de `Usuarios Simi.xlsx` no se importa: el modelo actual no tiene ese campo.
- Los PIN almacenados por Excel como números se convierten a texto y quedan marcados en el reporte para revisar posibles ceros iniciales perdidos en el archivo de origen.

## Resultado del ensayo con los cinco archivos entregados

El [reporte del dry-run](importacion_v11_dry_run.json) incluye el SHA-256 conjunto de los archivos, recuentos y observaciones por archivo, hoja y fila. No contiene contraseñas ni datos personales de usuarios. Después de limpiar los datos anteriores, previó 31 departamentos, 325 usuarios, 365 equipos sin usuario, 1270 IP libres, 200 anexos, 56 perfiles y 13 PCs. Se probó una carga completa en una copia temporal de la base de desarrollo y luego se ejecutó sobre la base del portal. Los recuentos posteriores coincidieron con el plan y quedaron 129 anexos sin usuario.

La limpieza de `core` conservó las cuentas y los roles de acceso. El [reporte de limpieza](limpieza_pre_import_v11.json) indica los recuentos eliminados y la ruta y SHA-256 del respaldo SQLite verificado.

La carga real está documentada en el [reporte de aplicación](importacion_v11_apply.json). Se creó un respaldo adicional de la base limpia, `db_limpia_antes_carga_v11_20260922_140710_067008.sqlite3`, antes de incorporar los 2260 registros.

Las filas omitidas o con campos omitidos se identifican mediante códigos en `issues`. Destacan 73 usuarios incompletos, 19 equipos sin identificador suficiente, 14 filas con serie duplicada y 16 perfiles incompletos o inválidos. El CSV contiene **todos** los equipos que sí se crearían, sin asignación de usuario.

## Ejecución

Antes de importar, configure el entorno habitual del backend con la **FIELD_ENCRYPTION_KEY existente** y haga una copia de seguridad de la base de destino. No genere una clave nueva para la base que ya contiene secretos.

```powershell
.\venv\Scripts\python.exe manage.py importar_datos_v11 --input-dir 'C:\Users\tiangelo\Downloads\Portal SimInfra\IMPORTAR' --dry-run --report '.\importacion_v11_dry_run.json'
```

Revise el reporte y el CSV. Para ejecutar sobre la base de destino se requiere `--apply` y el mismo SHA-256 mostrado por el último dry-run:

```powershell
.\venv\Scripts\python.exe manage.py importar_datos_v11 --input-dir 'C:\Users\tiangelo\Downloads\Portal SimInfra\IMPORTAR' --apply --expected-sha256 '<SHA-256 DEL DRY-RUN>' --report '.\importacion_v11_apply.json'
```

La carga se ejecuta en una sola transacción. Si una validación o escritura falla, se revierte completa. Las contraseñas importadas se cifran mediante el método existente del modelo; no se imprimen en la consola ni en el reporte.
