from django.db import migrations


def migrar_anexos_usuario(apps, schema_editor):
    Usuario = apps.get_model('core', 'Usuario')
    Anexo = apps.get_model('core', 'Anexo')
    HistorialAnexo = apps.get_model('core', 'HistorialAnexo')

    usuarios = (
        Usuario.objects
        .exclude(anexo__isnull=True)
        .exclude(anexo='')
    )

    for usuario in usuarios:
        numero_anexo = usuario.anexo.strip()

        if not numero_anexo:
            continue

        # Si el usuario ya está de BAJA,
        # el anexo se conserva pero queda disponible.
        if usuario.estado == 'BAJA':
            anexo = Anexo.objects.create(
                numero_anexo=numero_anexo,
                usuario=None,
                estado='DISPONIBLE'
            )

            HistorialAnexo.objects.create(
                anexo=anexo,
                usuario_anterior=usuario.nombre_completo,
                usuario_nuevo='Sin asignar',
                accion='MIGRACION',
                observacion='Anexo migrado desde Usuario y liberado por usuario en BAJA'
            )

        else:
            anexo = Anexo.objects.create(
                numero_anexo=numero_anexo,
                usuario_id=usuario.id,
                estado='ASIGNADO'
            )

            HistorialAnexo.objects.create(
                anexo=anexo,
                usuario_anterior='Sin asignar',
                usuario_nuevo=usuario.nombre_completo,
                accion='MIGRACION',
                observacion='Anexo migrado desde el campo antiguo Usuario.anexo'
            )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_anexo_historialanexo'),
    ]

    operations = [
        migrations.RunPython(
            migrar_anexos_usuario,
            migrations.RunPython.noop
        ),
    ]