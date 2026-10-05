# Compartir DEV desde el PC de la oficina

Para pruebas internas, el PC Windows `172.23.1.92` puede servir de puente entre
la red de oficina `172.23.1.0/24` y la VM `simidev` de Google Cloud. Los demás
PC abrirán `http://172.23.1.92:5178`. No hace falta permitir el puerto 5178
desde Internet en Google Cloud: el PC inicia una conexión SSH saliente a la VM
y publica **solo en su dirección de oficina** el puerto local 5178.

Esta opción depende de que el PC, las dos aplicaciones en la VM y el túnel SSH
sigan encendidos. El tráfico del navegador dentro de la oficina será HTTP; úsese
solo para DEV y pruebas internas. Para un servicio permanente corresponde el
proxy HTTPS descrito en [`ACCESO_OFICINA_DEV.md`](ACCESO_OFICINA_DEV.md).

## 1. Iniciar el portal en la VM

En la VM, abrir una terminal para Django:

```bash
cd /opt/Portal-Infraestructura-DEV
.venv/bin/daphne -b 127.0.0.1 -p 8005 config.asgi:application
```

En otra terminal, iniciar Vite:

```bash
cd /opt/Portal-Infraestructura-DEV/siminfra-frontend
npm run dev:lan
```

`siminfra-frontend/.env.local` debe tener `VITE_API_URL=/api` y
`PORTAL_LAN_HOST=10.0.0.28`. Si el puerto 5178 ya está en uso, no iniciar otra
copia de Vite: comprobar el proceso existente antes de cerrarlo. El `.env` local
de Django ya incluye `http://172.23.1.92:5178` en CORS y CSRF; reiniciar Django
para que tome ese cambio.

## 2. Autorizar el puerto en el firewall del PC

En el **PC Windows**, abrir **PowerShell como administrador** (no CMD) y
ejecutar una sola vez:

```powershell
New-NetFirewallRule -DisplayName 'Portal DEV puente SSH 5178' -Direction Inbound -Action Allow -Profile Domain,Private -Protocol TCP -LocalAddress 172.23.1.92 -LocalPort 5178 -RemoteAddress 172.23.1.0/24
```

Esta regla solo permite llegar al puerto 5178 de ese PC desde la subred de la
oficina. Si existe una política corporativa que bloquee reglas locales, pedir
apoyo a Infraestructura. Eliminar la regla cuando ya no se necesite:

```powershell
Get-NetFirewallRule -DisplayName 'Portal DEV puente SSH 5178' | Remove-NetFirewallRule
```

## 3. Abrir el puente SSH desde el PC

En otra ventana de **PowerShell del PC**, ejecutar el siguiente comando y dejar
la ventana abierta. La IP externa de `simidev` se confirmó el 3 de octubre de
2026; si cambia, reemplazarla. Si Windows se conecta a la VM mediante un alias
o configuración especial de SSH, usar ese alias en lugar de
`tiangelo@34.176.207.177`:

```powershell
ssh -N -T -g -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 172.23.1.92:5178:10.0.0.28:5178 tiangelo@34.176.207.177
```

`-L` enlaza **la IP del PC** con Vite en la VM; `-g` permite que otros PC de la
red lleguen al puerto reenviado. La terminal puede quedar sin mostrar salida:
es normal mientras el túnel esté activo. Cerrarla termina el acceso compartido.
No usar `0.0.0.0` como IP local.

## 4. Comprobar el acceso

Primero, en el PC que abre el túnel:

```powershell
Get-NetTCPConnection -LocalAddress 172.23.1.92 -LocalPort 5178 -State Listen
curl.exe -I http://172.23.1.92:5178
```

Después, desde otro PC de la misma subred:

```powershell
Test-NetConnection 172.23.1.92 -Port 5178
```

Si `TcpTestSucceeded` es `True`, abrir `http://172.23.1.92:5178` en el
navegador y probar inicio de sesión. Si el puerto escucha en el PC pero el otro
PC no llega, revisar firewall, perfil de red, aislamiento de clientes o rutas
entre subredes. Si el túnel abre pero aparece una página de error, comprobar que
Django y Vite siguen funcionando en la VM.

El `.env` local de DEV ya usa `PORTAL_PUBLIC_URL=http://172.23.1.92:5178` para
las etiquetas QR nuevas. Las etiquetas ya impresas con `10.0.0.28:5178`
seguirán apuntando a esa dirección privada de la VPC. Si cambia la IP del PC,
actualizar también `PORTAL_PUBLIC_URL`, los orígenes CORS/CSRF y la regla de
firewall; luego reiniciar Django y el túnel SSH.
