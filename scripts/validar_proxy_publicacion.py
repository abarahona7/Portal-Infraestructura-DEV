"""Prueba aislada del ejemplo Nginx; no cambia el servicio activo ni usa PROD."""

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
        }).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def request(port, path, *, https=True):
    if https:
        connection = http.client.HTTPSConnection(
            '127.0.0.1', port, timeout=3, context=ssl._create_unverified_context(),
        )
    else:
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def main():
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
                '-subj', '/CN=portal.example.cl',
            ], check=True, capture_output=True)

            http_port, https_port = free_port(), free_port()
            site = TEMPLATE.read_text()
            replacements = {
                'listen 80;': f'listen 127.0.0.1:{http_port};',
                'listen 443 ssl;': f'listen 127.0.0.1:{https_port} ssl;',
                '/etc/letsencrypt/live/portal.example.cl/fullchain.pem': str(certificate),
                '/etc/letsencrypt/live/portal.example.cl/privkey.pem': str(key),
                '/srv/portal/siminfra-frontend/dist': str(DIST),
                '/srv/portal/staticfiles/': str(temp / 'staticfiles') + '/',
                'http://127.0.0.1:8000': f'http://127.0.0.1:{backend.server_port}',
            }
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
                assert headers['Strict-Transport-Security'] == 'max-age=31536000'
                asset = re.search(rb'src="(/assets/[^"]+\.js)"', body).group(1).decode()
                status, headers, _ = request(https_port, asset)
                assert status == 200
                assert headers['Strict-Transport-Security'] == 'max-age=31536000'

                status, _, body = request(https_port, '/api/auth/me/')
                assert status == 200
                assert json.loads(body) == {'path': '/api/auth/me/', 'proto': 'https'}
                status, _, body = request(https_port, '/admin/')
                assert status == 200
                assert json.loads(body) == {'path': '/admin/', 'proto': 'https'}
                status, headers, body = request(https_port, '/static/probe.txt')
                assert status == 200 and body == b'static-ok'
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
