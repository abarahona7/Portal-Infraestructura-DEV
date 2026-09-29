from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F, Q, QuerySet

from core.models import (
    Anexo,
    AsignacionIP,
    Equipamiento,
    IP,
    PCGenerico,
    PerfilGenerico,
    Servidor,
    TipoAsignacionIP,
    Usuario,
)


@dataclass(frozen=True)
class IntegrityCheck:
    code: str
    description: str
    queryset: QuerySet


def build_checks():
    return [
        IntegrityCheck(
            'usuario_subarea_departamento',
            'Usuarios cuya subárea no pertenece a su departamento.',
            Usuario.objects.filter(subarea__isnull=False).exclude(
                subarea__departamento_id=F('departamento_id')
            ),
        ),
        IntegrityCheck(
            'perfil_subarea_departamento',
            'Perfiles cuya subárea no pertenece a su departamento.',
            PerfilGenerico.objects.filter(subarea__isnull=False).exclude(
                subarea__departamento_id=F('departamento_id')
            ),
        ),
        IntegrityCheck(
            'pc_subarea_departamento',
            'PCs genéricos cuya subárea no pertenece a su departamento.',
            PCGenerico.objects.filter(subarea__isnull=False).exclude(
                subarea__departamento_id=F('departamento_id')
            ),
        ),
        IntegrityCheck(
            'usuario_estado_invalido',
            'Usuarios con un estado fuera del catálogo permitido.',
            Usuario.objects.filter(
                Q(estado__isnull=True)
                | Q(estado='')
                | ~Q(estado__in=['ACTIVO', 'LICENCIA', 'BAJA'])
            ),
        ),
        IntegrityCheck(
            'equipo_estado_invalido',
            'Equipos con un estado fuera del catálogo permitido.',
            Equipamiento.objects.filter(
                Q(estado__isnull=True)
                | Q(estado='')
                | ~Q(estado__in=['ASIGNADO', 'STOCK', 'MANTENCION', 'BAJA'])
            ),
        ),
        IntegrityCheck(
            'perfil_estado_invalido',
            'Perfiles con un estado fuera del catálogo permitido.',
            PerfilGenerico.objects.filter(
                Q(estado__isnull=True)
                | Q(estado='')
                | ~Q(estado__in=['ACTIVO', 'INACTIVO'])
            ),
        ),
        IntegrityCheck(
            'usuario_baja_con_ip',
            'Usuarios de baja que todavía conservan una IP.',
            IP.objects.filter(usuario__estado='BAJA'),
        ),
        IntegrityCheck(
            'usuario_licencia_con_ip',
            'Usuarios con licencia médica que todavía conservan una IP.',
            IP.objects.filter(usuario__estado='LICENCIA'),
        ),
        IntegrityCheck(
            'usuario_baja_con_equipo',
            'Equipos todavía asignados a usuarios de baja.',
            Equipamiento.objects.filter(usuario__estado='BAJA'),
        ),
        IntegrityCheck(
            'usuario_baja_con_anexo',
            'Anexos todavía asignados a usuarios de baja.',
            Anexo.objects.filter(usuario__estado='BAJA'),
        ),
        IntegrityCheck(
            'anexo_estado_asignacion',
            'Anexos cuyo estado no coincide con la presencia de un usuario.',
            Anexo.objects.filter(
                Q(usuario__isnull=True, estado='ASIGNADO')
                | Q(usuario__isnull=False, estado='DISPONIBLE')
            ),
        ),
        IntegrityCheck(
            'equipo_estado_asignacion',
            'Equipos cuyo estado o fecha no coincide con su asignación.',
            Equipamiento.objects.filter(
                Q(usuario__isnull=True, estado='ASIGNADO')
                | Q(usuario__isnull=False, estado='STOCK')
                | Q(usuario__isnull=True, fecha_asignacion__isnull=False)
            ),
        ),
        IntegrityCheck(
            'ip_libre_con_asignacion',
            'IPs libres que conservan una asignación activa.',
            IP.objects.filter(
                estado='LIBRE',
                asignacion_activa__isnull=False,
            ),
        ),
        IntegrityCheck(
            'ip_reservada_sin_asignacion',
            'IPs reservadas sin una asignación central activa.',
            IP.objects.filter(
                estado='RESERVADA',
                asignacion_activa__isnull=True,
            ),
        ),
        IntegrityCheck(
            'ip_usuario_desincronizada',
            'Asignaciones de usuario que no coinciden con la IP proyectada.',
            AsignacionIP.objects.filter(
                tipo=TipoAsignacionIP.USUARIO
            ).exclude(ip__usuario_id=F('usuario_id')),
        ),
        IntegrityCheck(
            'ip_servidor_desincronizada',
            'Asignaciones de servidor que no coinciden con la IP proyectada.',
            AsignacionIP.objects.filter(
                tipo=TipoAsignacionIP.SERVIDOR
            ).exclude(servidor__ip_id=F('ip_id')),
        ),
        IntegrityCheck(
            'ip_pc_desincronizada',
            'Asignaciones de PC genérico que no coinciden con la IP proyectada.',
            AsignacionIP.objects.filter(
                tipo=TipoAsignacionIP.PC_GENERICO
            ).exclude(pc_generico__ip_id=F('ip_id')),
        ),
        IntegrityCheck(
            'ip_otro_desincronizada',
            'Asignaciones de otro uso que no coinciden con su descripción.',
            AsignacionIP.objects.filter(
                tipo=TipoAsignacionIP.OTRO
            ).exclude(ip__asignado_otro=F('detalle')),
        ),
        IntegrityCheck(
            'usuario_ip_sin_asignacion_central',
            'Usuarios con IP proyectada pero sin asignación central.',
            Usuario.objects.filter(
                ip__isnull=False,
                asignacion_ip_activa__isnull=True,
            ),
        ),
        IntegrityCheck(
            'servidor_ip_sin_asignacion_central',
            'Servidores con IP proyectada pero sin asignación central.',
            Servidor.objects.filter(
                ip__isnull=False,
                asignacion_ip_activa__isnull=True,
            ),
        ),
        IntegrityCheck(
            'pc_ip_sin_asignacion_central',
            'PCs genéricos con IP proyectada pero sin asignación central.',
            PCGenerico.objects.filter(
                ip__isnull=False,
                asignacion_ip_activa__isnull=True,
            ),
        ),
    ]


class Command(BaseCommand):
    help = (
        'Valida relaciones y estados críticos del portal sin modificar datos. '
        'Finaliza con error si encuentra una inconsistencia.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--muestras',
            type=int,
            default=10,
            help='Cantidad máxima de IDs de ejemplo por regla (predeterminado: 10).',
        )

    def handle(self, *args, **options):
        sample_size = max(options['muestras'], 0)
        failures = []
        checks = build_checks()

        self.stdout.write('Validando integridad funcional del portal...')

        for check in checks:
            count = check.queryset.count()
            if count == 0:
                self.stdout.write(self.style.SUCCESS(f'[OK] {check.code}'))
                continue

            sample = []
            if sample_size:
                sample = list(
                    check.queryset.order_by('pk').values_list(
                        'pk',
                        flat=True,
                    )[:sample_size]
                )

            failures.append((check, count, sample))
            sample_text = f' IDs: {sample}.' if sample else ''
            self.stdout.write(
                self.style.ERROR(
                    f'[ERROR] {check.code}: {count}. '
                    f'{check.description}{sample_text}'
                )
            )

        if failures:
            total = sum(count for _, count, _ in failures)
            raise CommandError(
                f'La validación encontró {total} inconsistencia(s) '
                f'en {len(failures)} regla(s).'
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Integridad confirmada: {len(checks)} reglas sin errores.'
            )
        )
