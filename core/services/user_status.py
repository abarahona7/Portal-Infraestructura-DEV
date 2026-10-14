"""Reglas centrales para cambios de estado de usuarios."""

from django.db import transaction

from core.audit import get_current_audit_username


def build_release_transition(user, previous_state, update_fields=None):
    """Captura los recursos antes de liberarlos por Baja o Licencia."""
    if update_fields is not None and 'estado' not in update_fields:
        return None
    if previous_state == user.estado or user.estado not in {'BAJA', 'LICENCIA'}:
        return None

    from core.models import Anexo, Equipamiento, IP

    resources = []
    if user.estado == 'BAJA':
        for equipment in Equipamiento.objects.filter(usuario=user).order_by('pk'):
            brand_model = ' '.join(filter(None, (equipment.marca, equipment.modelo)))
            resources.append({
                'clave': f'equipo:{equipment.pk}',
                'tipo': 'equipo',
                'id': equipment.pk,
                'nombre': ' · '.join(filter(None, (equipment.tipo, brand_model))),
                'detalle': equipment.numero_serie or equipment.af or 'Sin serie ni activo fijo',
            })

    for ip in IP.objects.filter(usuario=user).order_by('pk'):
        resources.append({
            'clave': f'ip:{ip.pk}',
            'tipo': 'ip',
            'id': ip.pk,
            'nombre': ip.direccion_ip,
            'detalle': 'Dirección IP liberada',
        })

    if user.estado == 'BAJA':
        for annex in Anexo.objects.filter(usuario=user).order_by('pk'):
            resources.append({
                'clave': f'anexo:{annex.pk}',
                'tipo': 'anexo',
                'id': annex.pk,
                'nombre': annex.numero_anexo,
                'detalle': 'Anexo liberado',
            })

    return {'motivo': user.estado, 'recursos': resources}


@transaction.atomic
def release_user_equipment(user):
    """Libera todos los equipos del usuario y conserva su auditoría normal."""
    from core.models import Equipamiento

    equipment = Equipamiento.objects.select_for_update().filter(usuario=user)
    for item in equipment:
        item.usuario = None
        item.estado = 'STOCK'
        item.fecha_asignacion = None
        item.save(update_fields=['usuario', 'estado', 'fecha_asignacion'])


def apply_user_status_rules(user, *, effective_state, transition, operation):
    """Libera relaciones, crea la revisión y publica el cambio del usuario."""
    from core.models import Anexo, HistorialUsuario, RevisionBajaUsuario
    from core.realtime import schedule_change
    from core.services.asignacion_ips import assign_ip_to_user

    if effective_state in {'BAJA', 'LICENCIA'}:
        assign_ip_to_user(user.pk, None)

    if effective_state == 'BAJA':
        release_user_equipment(user)
        for annex in Anexo.objects.select_for_update().filter(usuario=user):
            annex.usuario = None
            annex.save(update_fields=['usuario', 'estado'])

    if transition and transition['recursos']:
        actor = get_current_audit_username() or ''
        revision = RevisionBajaUsuario.objects.create(
            usuario=user,
            motivo=transition['motivo'],
            usuario_nombre=user.nombre_completo,
            usuario_red=user.usuario_red,
            recursos=transition['recursos'],
            creado_por=actor,
        )
        HistorialUsuario.objects.create(
            usuario=user,
            accion=f"REVISION_{transition['motivo']}_PENDIENTE",
            modificado_por=actor or None,
            modulo_relacionado='revisiones-baja',
            objeto_relacionado_id=str(revision.pk),
            observacion=(
                f"Pendiente revisar {len(transition['recursos'])} recurso(s) liberado(s)."
            ),
        )
        schedule_change(revision, 'created')

    schedule_change(user, operation)
