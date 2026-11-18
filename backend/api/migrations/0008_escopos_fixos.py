from collections import Counter

from django.db import migrations, models

CONVERSAO = {
    'Software': 'Web',
    'Design': 'Web',
    'Dados': 'Data Science',
    'Processos': 'Business Intelligence',
    'Hardware': 'Visão Computacional',
    'Pesquisa': 'AI',
}
ESCOPOS = ['Web', 'Data Science', 'Business Intelligence', 'Visão Computacional', 'AI']


def converter_escopos(apps, schema_editor):
    Alocacao = apps.get_model('api', 'Alocacao')

    for antigo, novo in CONVERSAO.items():
        Alocacao.objects.filter(escopo=antigo).update(escopo=novo)

    for alocacao in Alocacao.objects.exclude(escopo__in=ESCOPOS):
        da_equipe = Counter(
            Alocacao.objects.filter(projeto_id=alocacao.projeto_id, escopo__in=ESCOPOS)
            .values_list('escopo', flat=True)
        )
        alocacao.escopo = da_equipe.most_common(1)[0][0] if da_equipe else 'Web'
        alocacao.save(update_fields=['escopo'])


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0007_renomear_neo_empresarial'),
    ]

    operations = [
        migrations.RunPython(converter_escopos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='alocacao',
            name='escopo',
            field=models.CharField(
                choices=[
                    ('Web', 'Web'),
                    ('Data Science', 'Data Science'),
                    ('Business Intelligence', 'Business Intelligence'),
                    ('Visão Computacional', 'Visão Computacional'),
                    ('AI', 'AI'),
                ],
                max_length=60,
            ),
        ),
    ]
