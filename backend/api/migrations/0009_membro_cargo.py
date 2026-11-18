from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0008_escopos_fixos'),
    ]

    operations = [
        migrations.AddField(
            model_name='membro',
            name='cargo',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
    ]
