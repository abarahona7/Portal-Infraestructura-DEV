# Acceso estable al portal DEV desde la oficina

La oficina usa `172.23.1.0/24` y la VM `simidev` está en la VPC de Google Cloud,
con IP privada `10.0.0.28`. Actualmente no hay VPN entre ambas redes; por eso
`http://10.0.0.28:5178` no responde desde los PC de la oficina aunque el portal
funcione dentro de la VM. La opción elegida es publicar **solo HTTPS** para la
oficina, con una restricción por su IP pública de salida.

Este procedimiento corresponde únicamente a **DEV**. No cambia la base de datos,
QA ni producción. El archivo
[`deploy/nginx.portal-dev-oficina.conf.example`](../deploy/nginx.portal-dev-oficina.conf.example)
está preparado como ejemplo y **no está instalado** en Nginx. Los valores
`portal-dev.example.cl` y `203.0.113.10` son marcadores de ejemplo.

## Datos que debe confirmar Infraestructura

1. Nombre DNS exacto para DEV y certificado HTTPS válido para ese nombre,
   incluidos sus archivos y método de renovación. Como el ejemplo no abre HTTP
   en el puerto 80, la validación del certificado puede realizarse por DNS.
2. IP pública de salida de la oficina hacia esta VM (o el conjunto de IP/CIDR
   si la salida usa varios enlaces). La IP privada del PC `172.23.1.92` **no**
   sirve para esta regla. Para obtener una pista desde el PC de la oficina,
   ejecutar `curl https://api.ipify.org` en CMD; Infraestructura debe confirmar
   que esa es la salida usada para llegar al portal.
3. Permiso para crear o revisar la regla de entrada de Google Cloud en el
   proyecto `simidata-project-db-ws`, red `vpc-drsimi-db-ws`, etiqueta de la VM
   `simidev`. La cuenta de la VM no puede consultar/modificar el firewall por
   falta de alcance de autenticación.
4. Acceso de administración al Nginx de la VM y una forma de mantener el backend
   Waitress activo tras reinicios. La configuración Nginx vigente sigue siendo la
   predeterminada y no se ha modificado.

## Preparar la publicación en DEV

1. Crear el registro DNS de DEV hacia la IP externa de la VM o hacia el proxy
   corporativo que decida Infraestructura. Comprobar que el certificado coincide
   con ese nombre. Si se usa un balanceador o proxy adicional, la restricción
   debe aplicarse allí y se debe revisar qué IP real recibe Nginx.
2. En Google Cloud, permitir **TCP 443 únicamente desde la IP pública/CIDR de
   la oficina** hacia `simidev` y comprobar que ninguna regla de mayor alcance
   permita 443 desde Internet. No publicar TCP 8005 ni 5178. No es necesario
   publicar TCP 80 para este ejemplo. Infraestructura debe revisar el uso de la
   etiqueta `simidev` antes de crear una regla dirigida a ella.
3. Sustituir dominio, certificado e IP de oficina en el ejemplo Nginx. El
   frontend se sirve desde `siminfra-frontend/dist`; `/api/` y `/admin/` van al
   backend local `127.0.0.1:8005`. El proxy **reemplaza** `X-Forwarded-Proto` y
   `X-Forwarded-For` para que Django no use cabeceras enviadas por el cliente.
   Validar con `sudo nginx -t` antes de recargar Nginx. No copiar el ejemplo con
   las IP/dominio de muestra.
4. Compilar el frontend y generar estáticos de Django en la VM:

   ```bash
   cd /opt/Portal-Infraestructura-DEV/siminfra-frontend
   npm ci
   npm run build
   cd ..
   .venv/bin/python manage.py collectstatic --noinput
   ```

5. Iniciar Django con Waitress escuchando **solo** en `127.0.0.1:8005`, bajo el
   gestor de servicios que utilice Infraestructura. `runserver` y Vite son para
   desarrollo y no deben ser el servicio HTTPS estable:

   ```bash
   cd /opt/Portal-Infraestructura-DEV
   .venv/bin/waitress-serve --listen=127.0.0.1:8005 --threads=8 config.wsgi:application
   ```

   Antes de sustituir el proceso actual, comprobar la conexión MySQL DEV y el
   resultado de `manage.py check`; realizar el cambio en una ventana acordada.

6. Una vez que el dominio HTTPS responda, actualizar el `.env` local de DEV y
   reiniciar Waitress. Conservar las variables de base de datos y claves
   existentes; reemplazar solamente la configuración de URL/HTTPS necesaria:

   ```env
   DJANGO_ALLOWED_HOSTS=portal-dev.example.cl,127.0.0.1,localhost
   CORS_ALLOWED_ORIGINS=https://portal-dev.example.cl
   CSRF_TRUSTED_ORIGINS=https://portal-dev.example.cl
   PORTAL_PUBLIC_URL=https://portal-dev.example.cl
   USE_X_FORWARDED_PROTO=True
   SECURE_SSL_REDIRECT=True
   JWT_COOKIE_SECURE=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

   `PORTAL_PUBLIC_URL` determina el destino de las etiquetas QR nuevas. No
   cambiarlo antes de que la URL HTTPS funcione: las fichas impresas podrían
   apuntar a una dirección inaccesible. Si las etiquetas antiguas contienen
   `10.0.0.28:5178`, habrá que reimprimirlas o mantener temporalmente una ruta
   privada para quienes necesiten escanearlas.

## Comprobación después de activar

Desde un PC en la oficina, abrir `https://DOMINIO_DEV`, iniciar sesión y abrir
una ficha QR directa. En PowerShell se puede ejecutar
`Test-NetConnection DOMINIO_DEV -Port 443`; en CMD, `curl -I https://DOMINIO_DEV`.
Comprobar también que los usuarios **fuera** de la IP autorizada no pueden
acceder y que 8005/5178 no están publicados a Internet. Tras un reinicio de la
VM, repetir la comprobación para confirmar que Waitress, Nginx y el certificado
siguen operativos.

La configuración de ejemplo se valida sin tocar Nginx activo mediante:

```bash
.venv/bin/python scripts/validar_proxy_publicacion.py --office-dev
```
