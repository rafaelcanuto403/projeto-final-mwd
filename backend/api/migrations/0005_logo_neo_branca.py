from django.db import migrations

ANTIGA, NOVA = '/logos/neo.svg', '/logos/neo-branco.svg'


def aplicar(apps, schema_editor):
    EmpresaParceira = apps.get_model('api', 'EmpresaParceira')
    EmpresaParceira.objects.filter(nome='NEO', logo_url=ANTIGA).update(logo_url=NOVA)


def reverter(apps, schema_editor):
    EmpresaParceira = apps.get_model('api', 'EmpresaParceira')
    EmpresaParceira.objects.filter(nome='NEO', logo_url=NOVA).update(logo_url=ANTIGA)


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0004_logos_svg_brancas'),
    ]

    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
