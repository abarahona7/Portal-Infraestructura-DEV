from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('core', '0063_papeleraevento_contexto')]

    operations = [
        migrations.CreateModel(
            name='RevisionBajaUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('usuario_nombre', models.CharField(max_length=150)),
                ('usuario_red', models.CharField(max_length=50)),
                ('recursos', models.JSONField(default=list)),
                ('creado_por', models.CharField(blank=True, max_length=150)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('revisado_por', models.CharField(blank=True, max_length=150)),
                ('revisado_en', models.DateTimeField(blank=True, null=True)),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.usuario')),
            ],
            options={
                'ordering': ['-creado_en', '-pk'],
                'indexes': [models.Index(fields=['revisado_en', '-creado_en'], name='idx_rev_baja_pendiente')],
            },
        ),
    ]
