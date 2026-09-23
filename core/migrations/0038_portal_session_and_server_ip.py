from ipaddress import ip_address, ip_network

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


SERVER_NETWORK = ip_network('172.23.1.0/24')


def migrate_server_ips(apps, schema_editor):
    IP = apps.get_model('core', 'IP')
    Servidor = apps.get_model('core', 'Servidor')

    for servidor in Servidor.objects.all().iterator():
        raw_ip = (servidor.ip or '').strip()
        try:
            parsed_ip = ip_address(raw_ip)
        except ValueError:
            continue

        if parsed_ip not in SERVER_NETWORK:
            continue

        managed_ip, _ = IP.objects.get_or_create(
            direccion_ip=str(parsed_ip),
            defaults={'estado': 'LIBRE'},
        )

        if managed_ip.usuario_id or managed_ip.asignado_otro:
            continue

        servidor.ip_gestion_id = managed_ip.pk
        servidor.save(update_fields=['ip_gestion'])
        managed_ip.asignado_otro = f'Servidor: {servidor.hostname}'
        managed_ip.estado = 'RESERVADA'
        managed_ip.save(update_fields=['asignado_otro', 'estado'])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0037_perfilgenerico_departamento_subarea_estado'),
    ]

    operations = [
        migrations.CreateModel(
            name='PortalSession',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_activity', models.DateTimeField(default=django.utils.timezone.now)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='portal_sessions',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddField(
            model_name='servidor',
            name='ip_gestion',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='servidor',
                to='core.ip',
            ),
        ),
        migrations.RunPython(migrate_server_ips, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='servidor',
            name='ip',
        ),
        migrations.RenameField(
            model_name='servidor',
            old_name='ip_gestion',
            new_name='ip',
        ),
    ]
