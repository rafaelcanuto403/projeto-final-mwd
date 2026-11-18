from django.db import migrations

ANTIGO, NOVO = 'NEO', 'NEO Empresarial'


def renomear(apps, schema_editor):
    EmpresaParceira = apps.get_model('api', 'EmpresaParceira')
    if not EmpresaParceira.objects.filter(nome=NOVO).exists():
        EmpresaParceira.objects.filter(nome=ANTIGO).update(nome=NOVO)


def desfazer(apps, schema_editor):
    EmpresaParceira = apps.get_model('api', 'EmpresaParceira')
    if not EmpresaParceira.objects.filter(nome=ANTIGO).exists():
        EmpresaParceira.objects.filter(nome=NOVO).update(nome=ANTIGO)


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0006_empresa_comerc_energia'),
    ]

    operations = [
        migrations.RunPython(renomear, desfazer),
    ]
