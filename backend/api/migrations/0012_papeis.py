from django.db import migrations

# Admin não é um Group: é exclusivo do cargo AG PRJ (ver api/permissoes.py).
PAPEIS = ['gerente', 'membro']


def criar_papeis(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for nome in PAPEIS:
        Group.objects.get_or_create(name=nome)


def remover_papeis(apps, schema_editor):
    apps.get_model('auth', 'Group').objects.filter(name__in=PAPEIS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_membro_user'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(criar_papeis, remover_papeis),
    ]
