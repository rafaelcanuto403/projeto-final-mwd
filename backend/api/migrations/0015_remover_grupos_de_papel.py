from django.db import migrations

# Os papéis passaram a ser derivados (Admin = cargo AG PRJ; Membro = qualquer outro membro com
# login), e "gerente" virou a função do membro em cada projeto. Os Groups criados na 0012 não
# são mais usados.
GRUPOS = ['gerente', 'membro']


def remover_grupos(apps, schema_editor):
    apps.get_model('auth', 'Group').objects.filter(name__in=GRUPOS).delete()


def recriar_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for nome in GRUPOS:
        Group.objects.get_or_create(name=nome)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_funcao_e_gerente_unico'),
    ]

    operations = [
        migrations.RunPython(remover_grupos, recriar_grupos),
    ]
