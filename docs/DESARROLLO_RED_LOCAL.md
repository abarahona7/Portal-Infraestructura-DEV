# Desarrollo en red local

Este perfil permite que otras personas conectadas a la misma red abran el
portal desde sus navegadores. Está pensado únicamente para pruebas internas.

## Configuración de este equipo

La dirección IPv4 activa al preparar este perfil era `172.23.1.92` y el portal
queda disponible en:

```text
http://172.23.1.92:5173
```

El archivo local `.env` debe incluir la IP en estas variables:

```env
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,172.23.1.92
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://172.23.1.92:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://172.23.1.92:5173
```

`siminfra-frontend/.env.local` debe conservar esta configuración:

```env
VITE_API_URL=/api
```

De esta manera el navegador se comunica con la API mediante el proxy de Vite.
La sesión JWT, la protección CSRF y la cookie HttpOnly permanecen en el mismo
origen del portal.

## Iniciar el portal

Abrir una terminal en la raíz e iniciar Django:

```powershell
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Abrir una segunda terminal en `siminfra-frontend` e iniciar el perfil LAN:

```powershell
npm run dev:lan
```

Vite escuchará en `0.0.0.0:5173`, pero la API continuará accesible solamente
desde el equipo servidor a través del proxy.

## Autorizar el puerto en Windows

La primera vez, abrir PowerShell como administrador en la raíz del proyecto y
ejecutar:

```powershell
.\scripts\configurar_firewall_lan.ps1
```

El script autoriza únicamente `node.exe`, TCP 5173 y conexiones desde la
subred local en perfiles de red Dominio o Privado. El puerto 8000 no se publica.

Para eliminar posteriormente la regla:

```powershell
.\scripts\configurar_firewall_lan.ps1 -Remove
```

## Acceso desde otro equipo

1. Conectar el equipo a la misma red.
2. Abrir `http://172.23.1.92:5173` en el navegador.
3. Iniciar sesión normalmente.

Si la página no abre, comprobar que ambos equipos estén en la misma red y que
la regla `SimInfra Vite LAN (TCP 5173)` esté habilitada. La red corporativa de
este equipo utiliza actualmente el perfil Dominio.

## Si cambia la dirección IP

Ejecutar `ipconfig`, identificar la dirección IPv4 activa y reemplazar
`172.23.1.92` en las tres variables del `.env`. Reiniciar Django y Vite después
del cambio.

No se deben usar valores como `*` en `DJANGO_ALLOWED_HOSTS` ni habilitar todos
los orígenes CORS para resolver cambios de IP.
