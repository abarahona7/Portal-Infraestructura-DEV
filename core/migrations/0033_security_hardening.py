from django.db import migrations, models
import django.db.models.deletion

ROLE_NAMES = ['Visualizador', 'Operador Infraestructura', 'Administrador']

def create_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for name in ROLE_NAMES:
        Group.objects.get_or_create(name=name)

class Migration(migrations.Migration):
    dependencies = [('core', '0032_remove_usuario_ip_asignada')]
    operations = [
        migrations.CreateModel(
            name='SecurityAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.CharField(max_length=80)),
                ('actor', models.CharField(blank=True, max_length=150, null=True)),
                ('module', models.CharField(blank=True, max_length=80, null=True)),
                ('object_id_text', models.CharField(blank=True, max_length=80, null=True)),
                ('secret_type', models.CharField(blank=True, max_length=80, null=True)),
                ('success', models.BooleanField(default=False)),
                ('detail', models.CharField(blank=True, max_length=255, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterField(model_name='equipamiento', name='pin', field=models.CharField(blank=True, max_length=255, null=True)),
                migrations.AlterField(model_name='historialusuario', name='usuario', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historial', to='core.usuario')),
        migrations.AlterField(model_name='historialequipo', name='equipo', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historial', to='core.equipamiento')),
        migrations.AlterField(model_name='historialanexo', name='anexo', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historial', to='core.anexo')),
        migrations.AlterField(model_name='historialpcgenerico', name='pc', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historial', to='core.pcgenerico')),
        migrations.RunPython(create_roles, migrations.RunPython.noop),
    ]
