# Desarrollo en red local

Este perfil permite que otras personas conectadas a la misma red abran el
portal desde sus navegadores. Está pensado únicamente para pruebas internas.

## Configuración de este equipo

La IP privada actual de la VM DEV es `10.0.0.28`. Si cambia, actualiza las
variables indicadas abajo; el portal queda disponible en:

```text
http://10.0.0.28:5178
```

El archivo local `.env` debe incluir la IP en estas variables:

```env
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,simidev,10.0.0.28
CORS_ALLOWED_ORIGINS=http://localhost:5178,http://127.0.0.1:5178,http://10.0.0.28:5178
CSRF_TRUSTED_ORIGINS=http://localhost:5178,http://127.0.0.1:5178,http://10.0.0.28:5178
PORTAL_PUBLIC_URL=http://10.0.0.28:5178
```

`siminfra-frontend/.env.local` debe conservar esta configuración:

```env
VITE_API_URL=/api
PORTAL_LAN_HOST=10.0.0.28
```

De esta manera el navegador se comunica con la API mediante el proxy de Vite.
La sesión JWT, la protección CSRF y la cookie HttpOnly permanecen en el mismo
origen del portal.

## Iniciar el portal

Abrir una terminal en la raíz e iniciar Django:

```powershell
.\venv\Scripts\daphne.exe -b 127.0.0.1 -p 8005 config.asgi:application
```

En Linux, el comando equivalente es:

```bash
.venv/bin/daphne -b 127.0.0.1 -p 8005 config.asgi:application
```

Abrir una segunda terminal en `siminfra-frontend` e iniciar el perfil LAN:

```powershell
npm run dev:lan
```

Vite escuchará solo en `10.0.0.28:5178`; la API continuará accesible solamente
desde el equipo servidor a través del proxy. Si falta `PORTAL_LAN_HOST`, el
perfil LAN escuchará solo en `127.0.0.1` para evitar una exposición accidental.

Vite también reenvía `/ws/changes/` a Daphne. En DEV, sin
`PORTAL_CHANNEL_REDIS_URL`, se usa una capa de canales en memoria con un solo
proceso ASGI. Para varias instancias o producción se requiere Redis privado;
configurar `PORTAL_CHANNEL_REDIS_URL` y comprobar la reconexión tras reiniciar
Daphne. No exponer Redis ni el puerto 8005 a los navegadores.

## Autorizar el puerto en Windows

La primera vez, abrir PowerShell como administrador en la raíz del proyecto y
ejecutar:

```powershell
.\scripts\configurar_firewall_lan.ps1
```

El script autoriza únicamente `node.exe`, TCP 5178 y conexiones desde la
subred local en perfiles de red Dominio o Privado. El puerto 8005 no se publica.
Al configurarlo, también elimina la antigua regla de Vite para TCP 5176.

Para eliminar posteriormente la regla:

```powershell
.\scripts\configurar_firewall_lan.ps1 -Remove
```

## Acceso a la VM DEV desde la subred privada

Esta VM está en la subred `10.0.0.0/24` de la VPC `vpc-drsimi-db-ws` y tiene la
etiqueta `simidev`. En Google Cloud debe existir una regla de entrada que permita
**solo TCP 5178** desde `10.0.0.0/24` hacia esa etiqueta. No se necesita abrir
TCP 8005: Django escucha únicamente en `127.0.0.1` y Vite reenvía `/api`.
Infraestructura debe comprobar también que ninguna regla más amplia permita
TCP 5178 desde Internet. La cuenta de esta VM no tiene los permisos necesarios
para consultar o modificar esas reglas. Referencia:
[reglas de firewall de VPC](https://cloud.google.com/firewall/docs/using-firewalls).
Si la regla aún no existe, Infraestructura puede crearla con una cuenta autorizada:

```bash
gcloud compute firewall-rules create allow-simidev-dev-5178 \
  --project=simidata-project-db-ws \
  --network=vpc-drsimi-db-ws \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:5178 \
  --source-ranges=10.0.0.0/24 \
  --target-tags=simidev
```

Antes de ejecutarlo deben revisar las reglas existentes y confirmar que la
etiqueta `simidev` identifique solo las VM previstas. Si los usuarios entran
por una VPN cuyo rango de origen no es `10.0.0.0/24`, Infraestructura debe usar
el rango privado de esa VPN.

Desde otro equipo con ruta a esa VPC, comprobar:

```text
http://10.0.0.28:5178
```

## Acceso desde otro equipo

1. Conectar el equipo a la misma VPC de Google Cloud o a una VPN con ruta hacia
   `10.0.0.28`. La red interna de una oficina no es automáticamente esta VPC.
2. Abrir `http://10.0.0.28:5178` en el navegador.
3. Iniciar sesión normalmente.

Si la página no abre, comprobar que el otro equipo tenga ruta hacia
`10.0.0.28` y pedir a Infraestructura que revise la regla de VPC descrita arriba.
Desde el PC Windows, `ipconfig` muestra su IPv4 y este comando comprueba el
puerto sin depender del navegador:

```powershell
Test-NetConnection 10.0.0.28 -Port 5178
```

Si `TcpTestSucceeded` es `False` mientras el portal responde dentro de la VM,
falta ruta privada o una regla de entrada; cambiar CORS o el código del portal
no resolverá ese timeout. Para una oficina sin VPN, Infraestructura debe
habilitar una ruta privada o publicar un proxy HTTPS restringido a la oficina.
Para la publicación HTTPS de esta VM, consulte
[`ACCESO_OFICINA_DEV.md`](ACCESO_OFICINA_DEV.md).
Si se utilizará el PC Windows como puente temporal para la oficina, siga
[`PUENTE_PC_OFICINA_DEV.md`](PUENTE_PC_OFICINA_DEV.md).

## Si cambia la dirección IP

En Windows ejecutar `ipconfig`; en Linux, `ip -4 addr show`. Reemplazar
`10.0.0.28` en las cuatro variables del `.env` y en `PORTAL_LAN_HOST` de
`siminfra-frontend/.env.local`. Reiniciar Django y Vite después del cambio.

No se deben usar valores como `*` en `DJANGO_ALLOWED_HOSTS` ni habilitar todos
los orígenes CORS para resolver cambios de IP.
