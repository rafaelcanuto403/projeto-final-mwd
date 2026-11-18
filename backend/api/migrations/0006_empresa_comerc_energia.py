from django.db import migrations

NOME, LOGO = 'Comerc Energia', '/logos/comerc-energia.svg'


def criar(apps, schema_editor):
    EmpresaParceira = apps.get_model('api', 'EmpresaParceira')
    EmpresaParceira.objects.get_or_create(nome=NOME, defaults={'logo_url': LOGO})


def remover(apps, schema_editor):
    EmpresaParceira = apps.get_model('api', 'EmpresaParceira')
    EmpresaParceira.objects.filter(nome=NOME, projetos__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0005_logo_neo_branca'),
    ]

    operations = [
        migrations.RunPython(criar, remover),
    ]
