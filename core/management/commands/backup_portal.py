import os
import subprocess
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Genera un respaldo completo de la base de datos MySQL de DEV en /home/tiangelo/migracion/"

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='/home/tiangelo/migracion',
            help='Directorio de destino para el archivo .sql'
        )

    def handle(self, *args, **options):
        db_conf = settings.DATABASES['default']
        if db_conf['ENGINE'] != 'django.db.backends.mysql':
            raise CommandError("Este comando está diseñado para el motor MySQL en dev-simi.")

        dest_dir = Path(options['output_dir'])
        dest_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portalinfra_dev_backup_pre_itam_{timestamp}.sql"
        filepath = dest_dir / filename

        self.stdout.write(f"Iniciando respaldo de '{db_conf['NAME']}' en {filepath}...")

        env = os.environ.copy()
        env['MYSQL_PWD'] = db_conf['PASSWORD']

        cmd = [
            'mysqldump',
            '-h', db_conf['HOST'],
            '-P', str(db_conf['PORT']),
            '-u', db_conf['USER'],
            '--single-transaction',
            '--quick',
            '--routines',
            '--triggers',
            '--set-gtid-purged=OFF',
            db_conf['NAME'],
        ]

        try:
            fd = os.open(filepath, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                proc = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    check=False
                )

            if proc.returncode != 0:
                if filepath.exists():
                    filepath.unlink()
                raise CommandError(f"Error al ejecutar mysqldump: {proc.stderr}")

            filesize = filepath.stat().st_size
            filesize_kb = round(filesize / 1024, 2)
            self.stdout.write(self.style.SUCCESS(
                f"Respaldo generado exitosamente: {filepath} ({filesize_kb} KB)"
            ))

        except FileNotFoundError:
            raise CommandError("La utilidad 'mysqldump' no se encuentra instalada en el PATH del servidor.")
        except Exception as e:
            raise CommandError(f"Falla inesperada durante el respaldo: {str(e)}")
