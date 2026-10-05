import asyncio
import os
import secrets
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

with tempfile.TemporaryDirectory(prefix='portal_ws_smoke_') as folder:
    os.environ.update({
        'DJANGO_SETTINGS_MODULE': 'config.settings',
        'DJANGO_ENV': 'test',
        'DATABASE_ENGINE': 'sqlite',
        'SQLITE_PATH': folder + '/db.sqlite3',
        'DJANGO_SECRET_KEY': secrets.token_urlsafe(64),
        'FIELD_ENCRYPTION_KEY': Fernet.generate_key().decode(),
        'PORTAL_PUBLIC_URL': 'http://localhost:5178',
        'DJANGO_ALLOWED_HOSTS': 'testserver,localhost,127.0.0.1',
    })
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate', verbosity=0)
    from django.contrib.auth.models import User
    from core.models import PortalSession, Equipamiento
    from rest_framework_simplejwt.tokens import RefreshToken
    from config.asgi import application
    from channels.testing import WebsocketCommunicator
    from rest_framework.test import APIClient

    user = User.objects.create_superuser('probe', password='TestPassword123!')
    portal = PortalSession.objects.create(user=user)
    refresh = RefreshToken.for_user(user)
    refresh['sid'] = str(portal.pk)
    token = str(refresh.access_token)
    asset = Equipamiento.objects.create(tipo='Notebook', marca='Dell', modelo='Latitude', estado='STOCK')

    def edit_asset():
        client = APIClient()
        client.force_authenticate(user=user)
        return client.patch(
            f'/api/equipos/{asset.pk}/?categoria=Notebook',
            {'modelo': 'Latitude 2'}, format='json',
        )

    async def run_sync(pool, operation):
        job = pool.submit(operation)
        while not job.done():
            await asyncio.sleep(0.02)
        return job.result()

    async def main():
        clients = [
            WebsocketCommunicator(application, '/ws/changes/', headers=[(b'origin', b'http://localhost:5178')])
            for _ in range(2)
        ]
        for client in clients:
            assert (await client.connect(timeout=5))[0]
            await client.send_json_to({'type': 'auth', 'token': token})
            assert (await client.receive_json_from(timeout=5))['type'] == 'ready'
        with ThreadPoolExecutor(max_workers=1) as pool:
            response = await run_sync(pool, edit_asset)
        assert response.status_code == 200, getattr(response, 'data', response.status_code)
        for client in clients:
            event = await client.receive_json_from(timeout=5)
            assert event['type'] == 'change'
            assert event['record_id'] == asset.pk
            assert event['operation'] == 'updated'
            assert 'equipos' in event['modules']
            assert 'marca' not in event
            await client.disconnect()

        wrong_origin = WebsocketCommunicator(
            application, '/ws/changes/',
            headers=[(b'origin', b'https://sitio-ajeno.example')],
        )
        assert not (await wrong_origin.connect(timeout=5))[0]

        no_session = WebsocketCommunicator(
            application, '/ws/changes/',
            headers=[(b'origin', b'http://localhost:5178')],
        )
        assert (await no_session.connect(timeout=5))[0]
        await no_session.send_json_to({'type': 'auth', 'token': 'invalido'})
        rejected = await no_session.receive_output(timeout=5)
        assert rejected['type'] == 'websocket.close' and rejected['code'] == 4401

    asyncio.run(main())
    print('WebSocket, REST, dos clientes, origen y autenticación verificados en SQLite temporal.')
