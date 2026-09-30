"""Read-only verification of issued ITAM documents and their audit trail."""

import hashlib
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from core.models import ActaEntrega, ActaEstadoEvento, FolioContador, MovimientoActivo
from core.services.acta_estado_service import TRANSICIONES


REGLAS = {
    'folio_inconsistente': 'El folio no coincide con su año y correlativo.',
    'contador_desfasado': 'El contador anual es menor que un folio emitido o no existe.',
    'pdf_original_invalido': 'Falta el PDF original o su SHA-256 no coincide.',
    'snapshot_documento_inconsistente': 'El snapshot del documento no coincide con el acta.',
    'acta_movimientos_inconsistentes': 'El acta no tiene exactamente un movimiento.',
    'movimiento_acta_inconsistente': 'El movimiento no coincide con su acta o snapshot.',
    'evento_cadena_invalida': 'La secuencia de estados del acta es inválida.',
    'copia_firmada_invalida': 'La evidencia firmada falta o su SHA-256 no coincide.',
}


def verificar_integridad(*, muestras=10):
    """Return counts and sample primary keys per rule, without changing data."""
    resultados = {codigo: {'cantidad': 0, 'ids': []} for codigo in REGLAS}
    limite = max(muestras, 0)

    def registrar(codigo, pk):
        resultado = resultados[codigo]
        resultado['cantidad'] += 1
        if len(resultado['ids']) < limite:
            resultado['ids'].append(pk)

    contadores = {
        contador.anio: contador.ultimo_folio
        for contador in FolioContador.objects.filter(tipo_documento='ATI').only('anio', 'ultimo_folio')
    }
    estados = {}
    actas = {}
    movimientos_por_acta = defaultdict(int)
    for acta in ActaEntrega.objects.all().iterator(chunk_size=100):
        actas[acta.pk] = (acta.folio, acta.tipo_movimiento, acta.snapshot_documento)
        estados[acta.pk] = acta.estado
        if not 1 <= acta.numero_correlativo <= 999999 or acta.folio != f'ATI-{acta.anio}-{acta.numero_correlativo:06d}':
            registrar('folio_inconsistente', acta.pk)
        if contadores.get(acta.anio, -1) < acta.numero_correlativo:
            registrar('contador_desfasado', acta.pk)
        pdf = bytes(acta.documento_pdf or b'')
        if not pdf.startswith(b'%PDF-') or hashlib.sha256(pdf).hexdigest() != acta.hash_verificacion:
            registrar('pdf_original_invalido', acta.pk)
        documento = acta.snapshot_documento
        if not isinstance(documento, dict) or documento.get('folio') != acta.folio or documento.get('tipo_movimiento') != acta.tipo_movimiento:
            registrar('snapshot_documento_inconsistente', acta.pk)

    for movimiento in MovimientoActivo.objects.all().iterator(chunk_size=100):
        datos_acta = actas.get(movimiento.acta_id)
        if movimiento.acta_id is not None:
            movimientos_por_acta[movimiento.acta_id] += 1
        snapshot = movimiento.snapshot
        documento = snapshot.get('documento') if isinstance(snapshot, dict) else None
        if (
            datos_acta is None
            or movimiento.tipo_movimiento != datos_acta[1]
            or documento != datos_acta[2]
        ):
            registrar('movimiento_acta_inconsistente', movimiento.pk)
    for acta_id in actas:
        if movimientos_por_acta[acta_id] != 1:
            registrar('acta_movimientos_inconsistentes', acta_id)

    for evento in ActaEstadoEvento.objects.order_by('acta_id', 'pk').iterator(chunk_size=100):
        anterior = estados.get(evento.acta_id)
        siguiente = evento.estado_nuevo
        transicion_valida = (
            anterior == evento.estado_anterior
            and (
                (siguiente == 'ANULADA' and anterior != 'ANULADA' and bool(evento.motivo.strip()))
                or siguiente in TRANSICIONES.get(anterior, set())
            )
        )
        if not transicion_valida:
            registrar('evento_cadena_invalida', evento.pk)
        estados[evento.acta_id] = siguiente
        pdf = bytes(evento.copia_firmada_pdf or b'')
        if siguiente == 'FIRMADA':
            if not pdf.startswith(b'%PDF-') or hashlib.sha256(pdf).hexdigest() != evento.hash_copia_firmada:
                registrar('copia_firmada_invalida', evento.pk)
        elif pdf or evento.hash_copia_firmada:
            registrar('copia_firmada_invalida', evento.pk)
    return resultados


class Command(BaseCommand):
    help = 'Verifica folios, PDF, movimientos y eventos ITAM sin modificar datos.'

    def add_arguments(self, parser):
        parser.add_argument('--muestras', type=int, default=10,
                            help='Cantidad máxima de IDs de ejemplo por regla (predeterminado: 10).')

    def handle(self, *args, **options):
        resultados = verificar_integridad(muestras=options['muestras'])
        self.stdout.write('Validando integridad ITAM...')
        total = 0
        for codigo, descripcion in REGLAS.items():
            resultado = resultados[codigo]
            cantidad = resultado['cantidad']
            if cantidad:
                total += cantidad
                muestra = f" IDs: {resultado['ids']}." if resultado['ids'] else ''
                self.stdout.write(self.style.ERROR(f'[ERROR] {codigo}: {cantidad}. {descripcion}{muestra}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'[OK] {codigo}'))
        if total:
            raise CommandError(f'La validación ITAM encontró {total} inconsistencia(s).')
        self.stdout.write(self.style.SUCCESS(f'Integridad ITAM confirmada: {len(REGLAS)} reglas sin errores.'))
