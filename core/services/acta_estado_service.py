"""Transiciones de actas sin modificar el documento originalmente emitido."""
import hashlib
import json

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.audit import get_request_ip
from core.models import ActaEntrega, ActaEstadoEvento, SecurityAuditLog
from core.permissions import is_admin

MAX_COPIA_FIRMADA = 10 * 1024 * 1024
TRANSICIONES = {
    'GENERADA': {'PENDIENTE_FIRMA'},
    'PENDIENTE_FIRMA': {'FIRMADA'},
    'FIRMADA': {'CERRADA'},
    'CERRADA': set(),
    'ANULADA': set(),
}


def estado_vigente(acta):
    eventos = getattr(acta, '_eventos_estado', None)
    if eventos is not None:
        return eventos[0].estado_nuevo if eventos else acta.estado
    evento = acta.estado_eventos.only('estado_nuevo').first()
    return evento.estado_nuevo if evento else acta.estado


@transaction.atomic
def registrar_estado_acta(*, acta_id, estado_nuevo, usuario, motivo='', archivo_firmado=None, request=None):
    # El bloqueo del acta serializa las transiciones concurrentes de un mismo folio.
    acta = ActaEntrega.objects.select_for_update().get(pk=acta_id)
    anterior = estado_vigente(acta)
    motivo = (motivo or '').strip()
    if estado_nuevo == 'ANULADA':
        if not is_admin(usuario):
            raise PermissionDenied('Solo un administrador puede anular un acta.')
        if anterior == 'ANULADA':
            raise ValidationError({'estado_nuevo': 'Esta acta ya está anulada.'})
        if not motivo:
            raise ValidationError({'motivo': 'Indique el motivo de la anulación.'})
    elif estado_nuevo not in TRANSICIONES.get(anterior, set()):
        raise ValidationError({'estado_nuevo': f'No se permite pasar de {anterior} a {estado_nuevo}.'})
    if len(motivo) > 2000:
        raise ValidationError({'motivo': 'El motivo admite hasta 2000 caracteres.'})

    pdf = None
    if estado_nuevo == 'FIRMADA':
        if not archivo_firmado:
            raise ValidationError({'archivo_firmado': 'Adjunte la copia PDF firmada manualmente.'})
        if archivo_firmado.size > MAX_COPIA_FIRMADA:
            raise ValidationError({'archivo_firmado': 'El PDF supera el límite de 10 MB.'})
        if not archivo_firmado.name.lower().endswith('.pdf'):
            raise ValidationError({'archivo_firmado': 'El archivo debe tener extensión .pdf.'})
        pdf = archivo_firmado.read(MAX_COPIA_FIRMADA + 1)
        if len(pdf) > MAX_COPIA_FIRMADA or not pdf.startswith(b'%PDF-') or b'%%EOF' not in pdf[-1024:]:
            raise ValidationError({'archivo_firmado': 'Adjunte un PDF válido de hasta 10 MB.'})
    elif archivo_firmado:
        raise ValidationError({'archivo_firmado': 'La copia firmada solo se admite al marcar el acta como FIRMADA.'})

    evento = ActaEstadoEvento.objects.create(
        acta=acta, estado_anterior=anterior, estado_nuevo=estado_nuevo,
        usuario=usuario, motivo=motivo, copia_firmada_pdf=pdf,
        hash_copia_firmada=hashlib.sha256(pdf).hexdigest() if pdf else '',
    )
    SecurityAuditLog.objects.create(
        event=f'ESTADO_ACTA_{estado_nuevo}', actor=usuario.get_username(),
        module='ACTIVOS_ITAM', object_id_text=acta.folio, success=True,
        ip_address=get_request_ip(request),
        detail=json.dumps({
            'origen': 'API_ACTAS_ESTADO' if request is not None else 'SERVICIO_INTERNO',
            'acta_id': acta.pk, 'evento_id': evento.pk,
            'estado_anterior': anterior, 'estado_nuevo': estado_nuevo,
            'motivo': motivo, 'hash_copia_firmada': evento.hash_copia_firmada,
        }, ensure_ascii=False),
    )
    return evento
