import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membro',
            name='email',
            field=models.EmailField(max_length=160, unique=True),
        ),
        migrations.AlterField(
            model_name='membro',
            name='sigla',
            field=models.CharField(max_length=3, unique=True, validators=[django.core.validators.RegexValidator(message='A sigla deve ter exatamente 3 letras maiúsculas (ex.: RCN).', regex='^[A-Z]{3}$')]),
        ),
    ]
