from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0064_revisionbajausuario')]

    operations = [
        migrations.AddField(
            model_name='revisionbajausuario',
            name='motivo',
            field=models.CharField(
                choices=[('BAJA', 'Baja'), ('LICENCIA', 'Licencia Médica')],
                default='BAJA', max_length=20,
            ),
        ),
    ]
