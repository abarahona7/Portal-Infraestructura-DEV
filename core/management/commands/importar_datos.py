"""Marcador seguro para el importador heredado retirado."""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Importador heredado retirado. Use importar_datos_v11 con '
        '--dry-run antes de cualquier carga.'
    )

    def handle(self, *args, **options):
        raise CommandError(
            'El importador heredado fue retirado porque podía dejar cargas '
            'parciales y relacionar IP por coincidencias ambiguas. Use '
            '`python manage.py importar_datos_v11 --input-dir <directorio> '
            '--dry-run --report <reporte.json>` y aplique únicamente el '
            'reporte revisado.'
        )
