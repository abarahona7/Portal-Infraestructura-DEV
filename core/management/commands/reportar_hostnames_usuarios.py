from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand

from core.models import Usuario, _normalize_key


PLACEHOLDER_HOSTNAMES = {
    'na',
    'n/a',
    'n/i',
    'no aplica',
    'sin hostname',
}


class Command(BaseCommand):
    help = 'Genera un reporte de hostnames repetidos entre usuarios.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default='hostnames_usuarios_duplicados_v11.txt',
            help='Ruta del archivo TXT de salida.',
        )

    def handle(self, *args, **options):
        users = list(
            Usuario.objects.select_related('departamento')
            .exclude(hostname__isnull=True)
            .exclude(hostname='')
            .order_by('hostname', 'pk')
        )
        groups = defaultdict(list)
        for user in users:
            normalized = _normalize_key(user.hostname)
            if normalized:
                groups[normalized].append(user)

        duplicates = {
            hostname: items
            for hostname, items in groups.items()
            if len(items) > 1
        }
        affected = sum(len(items) for items in duplicates.values())
        lines = [
            'HOSTNAMES DUPLICADOS EN USUARIOS',
            '=' * 110,
            f'Usuarios revisados con hostname: {len(users)}',
            f'Grupos duplicados: {len(duplicates)}',
            f'Usuarios involucrados: {affected}',
            '',
            'Grupo | Motivo | ID | Usuario de red | Nombre | Departamento | Hostname original',
            '-' * 110,
        ]

        for group_number, (hostname, items) in enumerate(
            sorted(duplicates.items()),
            start=1,
        ):
            reason = (
                'MARCADOR GENERICO REPETIDO'
                if hostname in PLACEHOLDER_HOSTNAMES
                else 'HOSTNAME DUPLICADO'
            )
            for user in items:
                lines.append(' | '.join((
                    str(group_number),
                    reason,
                    str(user.pk),
                    user.usuario_red,
                    user.nombre_completo,
                    user.departamento.nombre,
                    user.hostname,
                )))

        output = Path(options['output']).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('\n'.join(lines) + '\n', encoding='utf-8-sig')
        self.stdout.write(self.style.SUCCESS(
            f'Reporte generado: {output} ({affected} usuarios).'
        ))
