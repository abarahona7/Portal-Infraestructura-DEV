"""Ejecuta QA con MySQL 8.4 desechable en Docker; nunca usa la base DEV.

Uso: python scripts/run_qa_mysql.py [módulo.test...]
Requiere la imagen mysql:8.4 local y acceso a Docker (directo o sudo -n).
"""

import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

from cryptography.fernet import Fernet
import MySQLdb


ROOT = Path(__file__).resolve().parent.parent


def docker_command():
    for prefix in (['docker'], ['sudo', '-n', 'docker']):
        try:
            result = subprocess.run(
                [*prefix, 'info', '--format', '{{.ServerVersion}}'],
                capture_output=True, text=True, check=False,
            )
        except FileNotFoundError:
            continue
        if result.returncode == 0:
            return prefix
    raise RuntimeError('Docker no está disponible; no se ejecutó ninguna prueba.')


def docker_output(command, *arguments):
    result = subprocess.run(
        [*command, *arguments], capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(f'Docker falló en {arguments[0]} (código {result.returncode}).')
    return result.stdout.strip()


def main():
    docker = docker_command()
    name = f'portal-qa-mysql-{secrets.token_hex(6)}'
    password = secrets.token_urlsafe(24)
    started = False
    try:
        docker_output(
            docker, 'run', '--rm', '-d', '--pull=never', '--name', name,
            '-p', '127.0.0.1::3306',
            '-e', f'MYSQL_ROOT_PASSWORD={password}',
            '-e', 'MYSQL_DATABASE=portal_qa_isolated',
            'mysql:8.4',
        )
        started = True
        details = json.loads(docker_output(
            docker, 'inspect', '--format', '{{json .NetworkSettings.Ports}}', name,
        ))
        port = int(details['3306/tcp'][0]['HostPort'])

        for _ in range(90):
            try:
                database = MySQLdb.connect(
                    host='127.0.0.1', port=port, user='root',
                    passwd=password, connect_timeout=2,
                )
                database.close()
                break
            except MySQLdb.Error:
                time.sleep(1)
        else:
            raise RuntimeError('MySQL temporal no quedó listo.')

        env = os.environ.copy()
        env.update({
            'DJANGO_SETTINGS_MODULE': 'config.settings',
            'DJANGO_ENV': 'test',
            'DATABASE_ENGINE': 'mysql',
            'DATABASE_NAME': 'portal_qa_isolated',
            'DATABASE_USER': 'root',
            'DATABASE_PASSWORD': password,
            'DATABASE_HOST': '127.0.0.1',
            'DATABASE_PORT': str(port),
            'DJANGO_SECRET_KEY': secrets.token_urlsafe(64),
            'FIELD_ENCRYPTION_KEY': Fernet.generate_key().decode('ascii'),
            'PORTAL_PUBLIC_URL': 'http://localhost:5178',
        })
        labels = sys.argv[1:] or ['core']
        return subprocess.run(
            [sys.executable, str(ROOT / 'manage.py'), 'test', *labels, '--noinput'],
            cwd=ROOT, env=env, check=False,
        ).returncode
    finally:
        if started:
            subprocess.run(
                [*docker, 'rm', '-f', name], capture_output=True,
                check=False,
            )


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc
