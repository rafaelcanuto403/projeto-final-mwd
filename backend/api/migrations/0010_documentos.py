import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0009_membro_cargo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Documento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('abertura', 'Documento de abertura'), ('contrato', 'Contrato'), ('proposta', 'Proposta'), ('relatorio', 'Relatório'), ('ata', 'Ata de reunião'), ('outro', 'Outro')], default='outro', max_length=20)),
                ('titulo', models.CharField(max_length=150)),
                ('arquivo', models.FileField(upload_to='documentos/%Y/%m/')),
                ('enviado_em', models.DateTimeField(auto_now_add=True)),
                ('projeto', models.ForeignKey(db_column='projeto_id', on_delete=django.db.models.deletion.CASCADE, related_name='documentos', to='api.projeto')),
            ],
            options={
                'db_table': 'documentos',
                'ordering': ['-enviado_em'],
            },
        ),
    ]
