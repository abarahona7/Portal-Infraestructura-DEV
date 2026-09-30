# Seguimiento de garantías ITAM en DEV

El maestro `Equipamiento` incorpora `fecha_vencimiento_garantia` como dato opcional. Se puede registrar al crear o editar cualquier tipo de equipo y aparece en la ficha autenticada del QR. Los activos existentes conservan la fecha vacía hasta que TI la registre; no se infiere a partir de la fecha de alta ni se altera ninguna acta histórica.

El Tablero de Activos muestra tres grupos de activos vigentes: garantía próxima a vencer (desde hoy hasta 30 días inclusive), vencida (antes de hoy) y sin fecha registrada. Los dados de baja quedan fuera de los tres grupos. Las listas de próximas y vencidas se pueden recorrer por páginas y permiten abrir la ficha para corregir la fecha o consultar el historial. `GET /api/activos/garantias/?estado=proximas|vencidas&page=1&page_size=20` usa los permisos actuales de Equipos (Operador Infraestructura o Administrador), evita caché y entrega solo identificación del activo, estado, fecha de vencimiento y días restantes. Las fechas se calculan según la zona horaria configurada en Django.

Esta etapa ofrece una alerta visual al abrir el tablero. No envía correos ni crea tareas programadas; esas automatizaciones requieren definir destinatarios y responsables. La fecha de garantía no forma parte del estado operativo ni modifica movimientos o folios.

La migración `0057_equipamiento_fecha_vencimiento_garantia_and_more` se aplicó en MySQL DEV después del respaldo `.local/backups/portalinfra_dev_backup_pre_itam_garantias_20260930_131934.sql`. La validación reversible es `.venv/bin/python manage.py shell < scripts/validar_garantias_itam.py`; cubre límites de la ventana, exclusión de bajas, ausencia de fecha, edición y permisos. QA queda pendiente de ambiente y acceso.
