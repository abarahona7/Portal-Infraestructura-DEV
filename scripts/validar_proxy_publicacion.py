"""Prueba aislada de ejemplos Nginx; no cambia el servicio activo ni usa PROD."""

import argparse
import http.client
import json
import re
import socket
import ssl
import subprocess
import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'deploy/nginx.portal.conf.example'
OFFICE_TEMPLATE = ROOT / 'deploy/nginx.portal-dev-oficina.conf.example'
DIST = ROOT / 'siminfra-frontend/dist'


def free_port():
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        return connection.getsockname()[1]


class MockBackend(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = json.dumps({
            'path': self.path,
            'proto': self.headers.get('X-Forwarded-Proto'),
            'client': self.headers.get('X-Forwarded-For'),
        }).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def request(port, path, *, https=True, headers=None, source_address=None):
    if https:
        connection = http.client.HTTPSConnection(
            '127.0.0.1', port, timeout=3, context=ssl._create_unverified_context(),
            source_address=source_address,
        )
    else:
        connection = http.client.HTTPConnection(
            '127.0.0.1', port, timeout=3, source_address=source_address,
        )
    try:
        connection.request('GET', path, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--office-dev', action='store_true')
    office_dev = parser.parse_args().office_dev
    if not (DIST / 'index.html').exists():
        raise RuntimeError('Ejecute npm run build antes de validar el proxy.')

    backend = HTTPServer(('127.0.0.1', 0), MockBackend)
    Thread(target=backend.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix='portal-nginx-check-') as directory:
            temp = Path(directory)
            certificate = temp / 'cert.pem'
            key = temp / 'key.pem'
            subprocess.run([
                'openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                '-keyout', str(key), '-out', str(certificate), '-days', '1',
                '-subj', '/CN=portal-dev.example.cl' if office_dev else '/CN=portal.example.cl',
            ], check=True, capture_output=True)

            http_port, https_port = free_port(), free_port()
            site = (OFFICE_TEMPLATE if office_dev else TEMPLATE).read_text()
            replacements = {
                'listen 443 ssl;': f'listen 127.0.0.1:{https_port} ssl;',
            }
            if office_dev:
                replacements.update({
                    '/etc/letsencrypt/live/portal-dev.example.cl/fullchain.pem': str(certificate),
                    '/etc/letsencrypt/live/portal-dev.example.cl/privkey.pem': str(key),
                    '/opt/Portal-Infraestructura-DEV/siminfra-frontend/dist': str(DIST),
                    '/opt/Portal-Infraestructura-DEV/staticfiles/': str(temp / 'staticfiles') + '/',
                    'http://127.0.0.1:8005': f'http://127.0.0.1:{backend.server_port}',
                    'allow 203.0.113.10;': 'allow 127.0.0.1;',
                })
            else:
                replacements.update({
                    'listen 80;': f'listen 127.0.0.1:{http_port};',
                    '/etc/letsencrypt/live/portal.example.cl/fullchain.pem': str(certificate),
                    '/etc/letsencrypt/live/portal.example.cl/privkey.pem': str(key),
                    '/srv/portal/siminfra-frontend/dist': str(DIST),
                    '/srv/portal/staticfiles/': str(temp / 'staticfiles') + '/',
                    'http://127.0.0.1:8000': f'http://127.0.0.1:{backend.server_port}',
                })
            for old, new in replacements.items():
                assert old in site, f'Falta en el ejemplo Nginx: {old}'
                site = site.replace(old, new)
            (temp / 'staticfiles').mkdir()
            (temp / 'staticfiles/probe.txt').write_text('static-ok')
            (temp / 'portal.conf').write_text(site)
            wrapper = temp / 'nginx.conf'
            wrapper.write_text(
                f'pid {temp}/nginx.pid;\nerror_log {temp}/error.log;\n'
                f'events {{}}\nhttp {{ access_log off; include {temp}/portal.conf; }}\n'
            )
            command = ['nginx', '-c', str(wrapper), '-p', str(temp)]
            syntax = subprocess.run(command + ['-t'], capture_output=True, text=True)
            assert syntax.returncode == 0, syntax.stderr

            process = subprocess.Popen(
                command + ['-g', 'daemon off;'],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            )
            try:
                for _ in range(40):
                    if process.poll() is not None:
                        raise RuntimeError(process.stderr.read())
                    try:
                        with socket.create_connection(('127.0.0.1', https_port), timeout=1):
                            break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Nginx temporal no inició.')

                status, headers, body = request(
                    https_port, '/qr/a/00000000-0000-0000-0000-000000000001',
                )
                assert status == 200 and b'<div id="root"></div>' in body
                if not office_dev:
                    assert headers['Strict-Transport-Security'] == 'max-age=31536000'
                asset = re.search(rb'src="(/assets/[^"]+\.js)"', body).group(1).decode()
                status, headers, _ = request(https_port, asset)
                assert status == 200
                if not office_dev:
                    assert headers['Strict-Transport-Security'] == 'max-age=31536000'

                status, _, body = request(
                    https_port, '/api/auth/me/',
                    headers={'X-Forwarded-For': '198.51.100.1'},
                )
                assert status == 200
                assert json.loads(body) == {
                    'path': '/api/auth/me/', 'proto': 'https', 'client': '127.0.0.1',
                }
                status, _, body = request(https_port, '/admin/')
                assert status == 200
                assert json.loads(body) == {
                    'path': '/admin/', 'proto': 'https', 'client': '127.0.0.1',
                }
                status, headers, body = request(https_port, '/static/probe.txt')
                assert status == 200 and body == b'static-ok'
                if office_dev:
                    for path in ('/api/auth/me/', '/qr/a/test', '/assets/no-existe.js'):
                        status, _, _ = request(
                            https_port, path, source_address=('127.0.0.2', 0),
                        )
                        assert status == 403, path
                    print('Nginx DEV aislado: HTTPS, QR, assets, API/admin e IP restringida OK')
                else:
                    assert headers['Strict-Transport-Security'] == 'max-age=31536000'
                    status, headers, _ = request(http_port, '/qr/a/test', https=False)
                    assert status == 301 and headers['Location'].endswith('/qr/a/test')
                    print('Nginx aislado: sintaxis, HTTPS, QR, assets, estáticos y proxy API/admin OK')
            finally:
                process.terminate()
                process.wait(timeout=5)
    finally:
        backend.shutdown()
        backend.server_close()


if __name__ == '__main__':
    main()
