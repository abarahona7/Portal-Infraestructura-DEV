# Checklist manual de QA y salida a producción

Ejecutar en un ambiente QA independiente. Registrar para cada prueba: resultado,
usuario ejecutor, fecha, evidencia y número de incidencia cuando falle.

## 1. Preparación

- [ ] Registrar URL, ambiente, rama y SHA exacto del commit probado.
- [ ] Confirmar que `git status` está limpio en el paquete desplegado.
- [ ] Confirmar MySQL 8.4, Redis privado, HTTPS y certificado vigente.
- [ ] Confirmar migraciones aplicadas hasta la última versión aprobada.
- [ ] Ejecutar `check --deploy`, `migrate --check` y `validar_integridad_portal`.
- [ ] Crear cuentas de prueba con roles Administrador, Operador y Visualizador.
- [ ] Preparar dos navegadores o equipos para pruebas simultáneas.
- [ ] Crear un usuario QA activo con notebook, celular, IP y anexo asignados.
- [ ] Mantener recursos libres para probar nuevas asignaciones.
- [ ] Crear y verificar un respaldo antes de modificar datos del ambiente.

## 2. Autenticación y sesiones

- [ ] Iniciar sesión con credenciales válidas.
- [ ] Rechazar credenciales inválidas sin revelar información sensible.
- [ ] Recargar la página y conservar una sesión vigente.
- [ ] Cerrar la sesión y bloquear el acceso usando el botón Atrás.
- [ ] Confirmar cierre automático después de cinco minutos sin actividad.
- [ ] Confirmar que cerrar sesión desconecta el WebSocket.
- [ ] Confirmar que tokens, claves y contraseñas no aparecen en consola ni logs.

## 3. Permisos

- [ ] Administrador puede operar todos los módulos autorizados.
- [ ] Administrador puede revelar secretos después de reautenticarse.
- [ ] Operador puede crear, editar, asignar y exportar donde corresponde.
- [ ] Operador no puede revelar secretos ni ejecutar retiros técnicos.
- [ ] Visualizador solo puede consultar Anexos asignados en una vista sin sidebar; no ve libres, filtros de estado, observaciones ni acciones.
- [ ] Probar rutas directas; ocultar un botón no debe ser la única protección.
- [ ] Confirmar respuesta `403` para acciones no autorizadas.

## 4. Usuarios

- [ ] Crear usuario; el estado aparece fijo como `ACTIVO`.
- [ ] Normalizar nombre, cargo y campos visuales en mayúsculas.
- [ ] Mantener usuario de red y correos en minúsculas.
- [ ] Mostrar `+569` fijo y permitir exactamente ocho dígitos restantes.
- [ ] Rechazar teléfonos inválidos o duplicados.
- [ ] Sincronizar la línea del usuario con su celular asignado.
- [ ] Editar una línea existente sin crear otra relación duplicada.
- [ ] Permitir una línea conocida aunque todavía no exista un celular identificado.
- [ ] Mostrar usuarios activos y con licencia en su departamento.
- [ ] Mostrar usuarios de Baja únicamente desde el acceso correspondiente.
- [ ] Probar búsqueda, departamento, estado, paginación y Excel.
- [ ] Confirmar que cada cambio aparece en el historial del usuario.

## 5. Licencia médica

- [ ] Abrir el cambio de estado para un usuario con IP asignada.
- [ ] Mostrar checklist solo para recursos realmente relacionados.
- [ ] Bloquear Guardar hasta confirmar todos los puntos visibles.
- [ ] Cambiar a `LICENCIA` y liberar únicamente la IP.
- [ ] Mantener notebook, celular, tablet y anexo asignados.
- [ ] Crear una notificación compartida por la IP liberada.
- [ ] Abrir la IP desde la notificación.
- [ ] Confirmar la revisión y disminuir el contador de la campana.
- [ ] Registrar estado, protocolo y liberación en los historiales.
- [ ] Repetir con un usuario sin IP; no mostrar confirmaciones inexistentes.

## 6. Baja y reactivación

- [ ] Cambiar a `BAJA` un usuario con equipos, IP y anexo.
- [ ] Mostrar checklist dinámico con sus recursos actuales.
- [ ] Bloquear Guardar hasta confirmar todos los puntos.
- [ ] Liberar IP y anexo.
- [ ] Desasignar todos los equipos e insumos relacionados.
- [ ] Crear una sola notificación con la lista completa de recursos.
- [ ] Abrir cada recurso desde la notificación.
- [ ] Confirmar que la baja no borra registros ni historiales.
- [ ] Confirmar la revisión y registrar quién la realizó.

Comportamiento aprobado para reactivación:

- [ ] Reactivar el usuario cambiando únicamente su estado a `ACTIVO`.
- [ ] No restaurar automáticamente equipos, IP ni anexo.
- [ ] Mostrar asignaciones anteriores solo como referencia histórica.
- [ ] Reasignar manualmente un recurso anterior si continúa disponible.
- [ ] Impedir la reasignación si ahora pertenece a otra persona.
- [ ] Registrar reactivación y nuevas asignaciones como eventos separados.

## 7. Equipos

- [ ] Probar Notebook, Celular, Tablet, Mac, BAM/Router y Periféricos.
- [ ] Mantener el tipo definido y bloqueado al crear desde una categoría.
- [ ] Limitar Periféricos a sus tipos permitidos.
- [ ] Aplicar las mismas validaciones de tipo desde la API.
- [ ] Mostrar el tipo en mayúsculas sin cambiar su valor interno.
- [ ] Permitir solo dígitos en Activo Fijo y respetar su longitud máxima.
- [ ] Mostrar `Sin AF`, `Sin número de serie` u otro texto equivalente al faltar datos.
- [ ] Rechazar serie, AF, IMEI o línea duplicados cuando corresponda.
- [ ] Impedir asignar equipos a usuarios de Baja o Licencia.
- [ ] Cambiar asignación y exigir checklist de movimiento.
- [ ] Cambiar estado y exigir checklist de movimiento.
- [ ] Verificar historial de creación, edición, asignación y liberación.
- [ ] Filtrar por departamento y comprobar el total mostrado.
- [ ] Abrir la ficha desde el listado y desde el tablero.

## 8. IP, servidores y PCs genéricos

- [ ] Asignar una IP libre a un usuario y reflejarla en ambos módulos.
- [ ] Liberarla y dejarla disponible nuevamente.
- [ ] Impedir dos propietarios activos para una misma IP.
- [ ] Impedir dos IP activas para el mismo propietario.
- [ ] Limitar servidores a `172.23.1.0/24` desde frontend y backend.
- [ ] Rechazar dirección de red y broadcast.
- [ ] Sincronizar IP al editar Servidor o PC Genérico.
- [ ] Impedir retirar una IP asignada.
- [ ] Permitir el retiro técnico de una IP libre.
- [ ] Confirmar historial de asignaciones y liberaciones.
- [ ] Confirmar que el historial IP no muestra el botón Exportar Excel.

## 9. Anexos y perfiles genéricos

- [ ] Asignar un anexo disponible y reflejarlo en el usuario.
- [ ] Cambiar o liberar el anexo sin dejar dos asignaciones activas.
- [ ] Impedir asignar un anexo a un usuario de Baja.
- [ ] Crear, editar, desactivar y reactivar un perfil genérico.
- [ ] Mostrar perfiles inactivos mediante su filtro correspondiente.
- [ ] Confirmar historial y permisos de ambos módulos.

## 10. Notificaciones y tiempo real

- [ ] Abrir dos sesiones autorizadas en navegadores diferentes.
- [ ] Cambiar un registro en la primera sesión.
- [ ] Actualizar listado, ficha, tablero y campana en la segunda sin F5.
- [ ] Crear solo una notificación por baja o licencia.
- [ ] Compartir el estado pendiente entre todo el equipo de Infraestructura.
- [ ] Exigir confirmar todos los recursos antes de cerrar una revisión.
- [ ] Cortar y restaurar la red; reconectar WebSocket automáticamente.
- [ ] Evitar duplicar eventos después de la reconexión.
- [ ] Confirmar que un Visualizador no recibe eventos prohibidos.

## 11. Ediciones simultáneas

- [ ] Abrir el mismo registro en dos sesiones.
- [ ] Guardar un cambio desde la primera sesión.
- [ ] Intentar guardar el formulario antiguo desde la segunda.
- [ ] Recibir `409 Conflict` y un mensaje comprensible.
- [ ] Cerrar el formulario antiguo y recargar la información reciente.
- [ ] Conservar el primer cambio sin sobrescritura.
- [ ] Repetir con Usuario, Equipo, IP y Departamento/Área.

## 12. Tablero de activos

- [ ] Comparar totales con los listados de equipos.
- [ ] Mostrar todos los departamentos sin cortar palabras.
- [ ] Ordenar barras de mayor a menor.
- [ ] Abrir un departamento desde el gráfico.
- [ ] Abrir cada grupo de atención y revisar sus equipos.
- [ ] Actualizar automáticamente después de modificar un equipo.
- [ ] Confirmar que no existe botón manual Actualizar.
- [ ] Confirmar que no aparece el estado En reparación.

## 13. QR, PDF y Excel

- [ ] Escanear físicamente un QR con un teléfono autorizado en la red.
- [ ] Exigir inicio de sesión antes de mostrar la ficha.
- [ ] Probar equipo asignado y equipo sin usuario.
- [ ] Conservar el mismo QR después de editar el equipo.
- [ ] Abrir directamente `/qr/a/<uuid>` sin recibir `404`.
- [ ] Descargar el acta y revisar visualmente nombres, equipos y campos vacíos.
- [ ] Mostrar `Sin AF` y valores equivalentes en el acta.
- [ ] Abrir cada Excel exportado y revisar encabezados, acentos y cantidad de filas.

## 14. Responsive y experiencia visual

- [ ] Probar anchos de 320, 375, 768, 1024, 1366 y 1920 px.
- [ ] Probar zoom del navegador en 75%, 100%, 125%, 150% y 200%.
- [ ] Evitar scroll horizontal en páginas y modales.
- [ ] Mantener botones, filtros y tablas utilizables.
- [ ] Bloquear el scroll de fondo mientras un modal está abierto.
- [ ] Permitir cerrar modales con botón, Escape y acción Cancelar.
- [ ] Mantener sidebar utilizable sin ocultar opciones importantes.
- [ ] Revisar foco visible, etiquetas y navegación con teclado.

## 15. Infraestructura y recuperación

- [ ] Servir todo el portal mediante HTTPS.
- [ ] Redirigir HTTP a HTTPS.
- [ ] Mantener Daphne, MySQL y Redis inaccesibles desde clientes externos.
- [ ] Probar `/api`, `/ws/`, `/admin/`, `/static/` y rutas SPA mediante Nginx.
- [ ] Reiniciar backend y confirmar recuperación automática de systemd.
- [ ] Reiniciar el servidor y confirmar arranque automático del portal.
- [ ] Revisar logs JSON y correlación mediante `X-Request-ID`.
- [ ] Verificar respaldo diario y copia fuera del servidor.
- [ ] Restaurar un respaldo en una base aislada.
- [ ] Confirmar que la clave Fernet respaldada puede descifrar los secretos.
- [ ] Ensayar rollback al commit anterior.

## 16. Criterio de aprobación

- [ ] No existen fallos críticos ni altos abiertos.
- [ ] Los fallos medios tienen responsable y fecha acordada.
- [ ] Integridad, migraciones, build y pruebas automatizadas están correctos.
- [ ] Infraestructura, QA y dueño funcional firman la evidencia.
- [ ] El commit aprobado se integra en `main` sin cambios posteriores.
- [ ] Se crea un tag y se despliega exactamente el commit aprobado.
