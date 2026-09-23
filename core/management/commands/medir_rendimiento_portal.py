import json
import statistics
from time import perf_counter

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient


ENDPOINTS = {
    'usuarios': '/api/usuarios/',
    'equipos': '/api/equipos/',
    'ips': '/api/ips/',
    'anexos': '/api/anexos/',
    'perfiles': '/api/perfiles-genericos/',
    'pcs_genericos': '/api/pcs-genericos/',
    'servidores': '/api/servidores/',
    'departamentos': '/api/departamentos/',
    'datos_referencia': '/api/reference-data/',
    'referencia_inicio_usuarios': (
        '/api/reference-data/?include=usuarios,departamentos'
    ),
}


class Command(BaseCommand):
    help = 'Mide tiempo, consultas SQL y tamaño de respuesta de los endpoints principales.'

    def add_arguments(self, parser):
        parser.add_argument('--repeticiones', type=int, default=3)
        parser.add_argument('--salida')

    @override_settings(DEBUG=True, ALLOWED_HOSTS=['testserver'])
    def handle(self, *args, **options):
        repetitions = max(1, options['repeticiones'])
        user = get_user_model().objects.filter(is_superuser=True).first()
        if not user:
            raise CommandError('Se necesita un superusuario para ejecutar la medición.')

        client = APIClient()
        client.force_authenticate(user=user)
        report = {
            'repeticiones': repetitions,
            'endpoints': {},
        }

        for name, url in ENDPOINTS.items():
            samples = []
            for _ in range(repetitions):
                with CaptureQueriesContext(connection) as queries:
                    started_at = perf_counter()
                    response = client.get(url)
                    body = response.content
                    elapsed_ms = (perf_counter() - started_at) * 1000

                if response.status_code != 200:
                    raise CommandError(
                        f'{url} respondió HTTP {response.status_code}: '
                        f'{body[:300]!r}'
                    )

                samples.append({
                    'tiempo_ms': round(elapsed_ms, 2),
                    'consultas_sql': len(queries),
                    'bytes': len(body),
                })

            report['endpoints'][name] = {
                'url': url,
                'tiempo_mediana_ms': round(
                    statistics.median(item['tiempo_ms'] for item in samples),
                    2,
                ),
                'consultas_sql_mediana': int(
                    statistics.median(item['consultas_sql'] for item in samples)
                ),
                'bytes': samples[-1]['bytes'],
                'muestras': samples,
            }

        rendered = json.dumps(report, indent=2, ensure_ascii=False)
        if options.get('salida'):
            with open(options['salida'], 'w', encoding='utf-8') as output_file:
                output_file.write(rendered)
                output_file.write('\n')

        self.stdout.write(rendered)
