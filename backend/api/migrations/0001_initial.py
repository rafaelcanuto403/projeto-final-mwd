import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='EmpresaParceira',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, unique=True)),
                ('logo_url', models.CharField(blank=True, max_length=500, null=True)),
            ],
            options={
                'verbose_name': 'Empresa parceira',
                'verbose_name_plural': 'Empresas parceiras',
                'db_table': 'empresas_parceiras',
            },
        ),
        migrations.CreateModel(
            name='Membro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sigla', models.CharField(max_length=3, unique=True)),
                ('nome', models.CharField(max_length=120)),
                ('email', models.CharField(max_length=160, unique=True)),
                ('foto_url', models.CharField(blank=True, max_length=500, null=True)),
            ],
            options={
                'db_table': 'membros',
            },
        ),
        migrations.CreateModel(
            name='Projeto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150)),
                ('descricao', models.CharField(blank=True, max_length=500, null=True)),
                ('status', models.CharField(choices=[('planejamento', 'Planejamento'), ('em_andamento', 'Em andamento'), ('concluido', 'Concluído')], default='planejamento', max_length=20)),
                ('data_inicio', models.DateField()),
                ('data_fim_prevista', models.DateField(blank=True, null=True)),
                ('empresa', models.ForeignKey(db_column='empresa_id', on_delete=django.db.models.deletion.PROTECT, related_name='projetos', to='api.empresaparceira')),
            ],
            options={
                'db_table': 'projetos',
            },
        ),
        migrations.CreateModel(
            name='Alocacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('funcao', models.CharField(max_length=60)),
                ('escopo', models.CharField(max_length=60)),
                ('membro', models.ForeignKey(db_column='membro_id', on_delete=django.db.models.deletion.CASCADE, related_name='alocacoes', to='api.membro')),
                ('projeto', models.ForeignKey(db_column='projeto_id', on_delete=django.db.models.deletion.CASCADE, related_name='alocacoes', to='api.projeto')),
            ],
            options={
                'verbose_name': 'Alocação',
                'verbose_name_plural': 'Alocações',
                'db_table': 'alocacoes',
            },
        ),
    ]
