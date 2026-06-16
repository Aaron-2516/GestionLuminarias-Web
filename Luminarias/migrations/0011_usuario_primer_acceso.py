# Generated migration for adding primer_acceso field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Luminarias', '0010_alter_asignacionzona_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='primer_acceso',
            field=models.BooleanField(default=True),
        ),
    ]
