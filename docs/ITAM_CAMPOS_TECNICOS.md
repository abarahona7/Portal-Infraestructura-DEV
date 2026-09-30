# Datos técnicos por tipo de activo

El alta manual de un Celular requiere IMEI. El alta de un Notebook o Mac requiere Hostname y MAC Address. El formulario muestra estos campos según el tipo y la API vuelve a validarlos, incluso si el cliente omite los controles del navegador. Al cambiar un equipo existente hacia uno de esos tipos se aplica la misma exigencia. Un dato técnico ya registrado tampoco puede borrarse dejando el equipo en ese tipo.

El maestro legado no se reescribe: sus equipos incompletos pueden continuar editándose sin exigir una carga retroactiva de IMEI o MAC. Al cambiar el tipo desde el formulario, se limpian los identificadores que dejan de corresponder. No se introduce migración ni se modifica el flujo de movimientos, folios o actas.

La verificación reversible en DEV es `.venv/bin/python manage.py shell < scripts/validar_campos_tecnicos_activos.py`. El respaldo previo a este ajuste quedó en `.local/backups/portalinfra_dev_backup_pre_itam_campos_tecnicos_20260930_030020.sql`. QA sigue pendiente de ambiente y permisos.
