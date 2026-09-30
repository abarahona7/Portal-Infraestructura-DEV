# Alta trazable y puertos de desarrollo

Al crear un equipo disponible desde `POST /api/equipos/`, el portal registra automáticamente un movimiento `ALTA`, su folio ATI, el PDF y la auditoría. El movimiento inicial conserva `antes: null` y el estado del activo tras su ingreso. La creación y estos registros comparten una transacción: si falla el folio o el PDF, el activo tampoco queda creado. El alta no puede repetirse sobre un activo que ya tenga movimientos. Los equipos anteriores no reciben un alta inventada retroactivamente; conservan su historia existente.

La prueba reversible `.venv/bin/python manage.py shell < scripts/validar_alta_activo_transaccional.py` comprueba la emisión, integridad, bloqueo de duplicados y rollback ante una falla documental. No se añade migración. El respaldo previo quedó en `.local/backups/portalinfra_dev_backup_pre_itam_alta_puertos_20260930_114603.sql`.

En este DEV, Django escucha solo en `127.0.0.1:8008` y Vite en `0.0.0.0:5176`. El proxy de Vite envía `/api` a Django; el navegador debe abrir `http://localhost:5176` mediante el túnel SSH habitual. Para iniciar ambos manualmente:

```bash
.venv/bin/python manage.py runserver 127.0.0.1:8008
```

En otra terminal:

```bash
cd siminfra-frontend && npm run dev:lan
```

El `.env` local usa el puerto 5176 en los orígenes CORS/CSRF y en `PORTAL_PUBLIC_URL`; este último determina la dirección impresa en las etiquetas QR. Si los lectores abrirán el portal desde otro host, se debe configurar allí la URL que podrán alcanzar antes de imprimir etiquetas. Los procesos ajenos que ocupan 8000 y 5173 no se modificaron.
