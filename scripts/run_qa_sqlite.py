"""Ejecuta la suite QA en una base SQLite desechable, sin tocar DEV.

Uso: python scripts/run_qa_sqlite.py [módulo.test...]
"""

import os
from pathlib import Path
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory

from cryptography.fernet import Fernet


ROOT = Path(__file__).resolve().parent.parent


def main():
    with TemporaryDirectory(prefix='portal_qa_sqlite_') as directory:
        database = Path(directory) / 'qa.sqlite3'
        env = os.environ.copy()
        env.update({
            'DJANGO_SETTINGS_MODULE': 'config.settings',
            'DJANGO_ENV': 'test',
            'DATABASE_ENGINE': 'sqlite',
            'SQLITE_PATH': str(database),
            'DJANGO_SECRET_KEY': secrets.token_urlsafe(64),
            'FIELD_ENCRYPTION_KEY': Fernet.generate_key().decode('ascii'),
            'PORTAL_PUBLIC_URL': 'http://localhost:5178',
        })
        labels = sys.argv[1:] or ['core']
        command = [sys.executable, str(ROOT / 'manage.py'), 'test', *labels, '--noinput']
        return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
