from django.db import migrations

NOVAS = {
    'WEG': ('/logos/weg.jpg', '/logos/weg.svg'),
    'Embraco/Nidec': ('/logos/embraco-nidec.webp', '/logos/embraco-nidec.svg'),
    'Landis+Gyr': ('/logos/landis-gyr.png', '/logos/landis-gyr.svg'),
    'CERTI': ('/logos/certi.png', '/logos/certi.svg'),
}


def aplicar(apps, schema_editor):
    EmpresaParceira = apps.get_model('api', 'EmpresaParceira')
    for nome, (antiga, nova) in NOVAS.items():
        EmpresaParceira.objects.filter(nome=nome, logo_url=antiga).update(logo_url=nova)


def reverter(apps, schema_editor):
    EmpresaParceira = apps.get_model('api', 'EmpresaParceira')
    for nome, (antiga, nova) in NOVAS.items():
        EmpresaParceira.objects.filter(nome=nome, logo_url=nova).update(logo_url=antiga)


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0003_empresas_iniciais'),
    ]

    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
