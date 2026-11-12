from django.db import migrations

# Carga inicial das empresas parceiras atuais.
# As logos ficam em frontend/public/logos/ e são servidas pelo Vite na raiz ("/logos/...").
EMPRESAS = [
    ('WEG', '/logos/weg.jpg'),
    ('Embraco/Nidec', '/logos/embraco-nidec.webp'),
    ('Landis+Gyr', '/logos/landis-gyr.png'),
    ('CERTI', '/logos/certi.png'),
    ('NEO', '/logos/neo.svg'),
]


def criar_empresas(apps, schema_editor):
    EmpresaParceira = apps.get_model('api', 'EmpresaParceira')
    for nome, logo_url in EMPRESAS:
        EmpresaParceira.objects.update_or_create(nome=nome, defaults={'logo_url': logo_url})


def remover_empresas(apps, schema_editor):
    EmpresaParceira = apps.get_model('api', 'EmpresaParceira')
    EmpresaParceira.objects.filter(nome__in=[nome for nome, _ in EMPRESAS], projetos__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_alter_membro_email_alter_membro_sigla'),
    ]

    operations = [
        migrations.RunPython(criar_empresas, remover_empresas),
    ]
