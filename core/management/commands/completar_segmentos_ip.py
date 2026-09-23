"""Completa los hosts utilizables de los segmentos IP administrados."""

import ipaddress

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import IP


SEGMENTS = (
    '172.24.1.0/24',
    '192.168.30.0/24',
)


class Command(BaseCommand):
    help = 'Crea las IP faltantes (hosts 1 a 254) como LIBRE y sin asignación.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Confirma la escritura. Sin esta opción solo se muestra la planificación.',
        )

    def handle(self, *args, **options):
        planned = {}
        missing_addresses = []

        for cidr in SEGMENTS:
            network = ipaddress.ip_network(cidr)
            addresses = [str(address) for address in network.hosts()]
            existing = set(
                IP.objects.filter(direccion_ip__in=addresses)
                .values_list('direccion_ip', flat=True)
            )
            missing = [address for address in addresses if address not in existing]
            planned[cidr] = {
                'existentes': len(existing),
                'por_crear': len(missing),
                'total_final': len(addresses),
            }
            missing_addresses.extend(missing)

        for cidr, summary in planned.items():
            self.stdout.write(
                f'{cidr}: {summary["existentes"]} existentes, '
                f'{summary["por_crear"]} por crear, '
                f'{summary["total_final"]} total final.'
            )

        if not options['apply']:
            self.stdout.write('Previsualización completada. No se modificó la base de datos.')
            return

        with transaction.atomic():
            IP.objects.bulk_create(
                [
                    IP(
                        direccion_ip=address,
                        estado='LIBRE',
                        usuario=None,
                        asignado_otro=None,
                        observacion=None,
                    )
                    for address in missing_addresses
                ],
                ignore_conflicts=True,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Segmentos completados: {len(missing_addresses)} IP creadas.'
            )
        )
