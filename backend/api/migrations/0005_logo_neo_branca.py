from django.db import migrations

# Logo do NEO em branco com a seta vazada (a original laranja vira um círculo branco com o filtro CSS).
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
