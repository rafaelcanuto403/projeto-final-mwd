from django.core.validators import RegexValidator
from django.db import models


class EmpresaParceira(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    logo_url = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'empresas_parceiras'
        verbose_name = 'Empresa parceira'
        verbose_name_plural = 'Empresas parceiras'

    def __str__(self):
        return self.nome


class Membro(models.Model):
    sigla = models.CharField(
        max_length=3,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{3}$',
                message='A sigla deve ter exatamente 3 letras maiúsculas (ex.: RCN).',
            )
        ],
    )
    nome = models.CharField(max_length=120)
    email = models.EmailField(max_length=160, unique=True)
    foto_url = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'membros'

    def __str__(self):
        return f'{self.sigla} - {self.nome}'


class Projeto(models.Model):
    class Status(models.TextChoices):
        PLANEJAMENTO = 'planejamento', 'Planejamento'
        EM_ANDAMENTO = 'em_andamento', 'Em andamento'
        CONCLUIDO = 'concluido', 'Concluído'

    nome = models.CharField(max_length=150)
    descricao = models.CharField(max_length=500, blank=True, null=True)
    empresa = models.ForeignKey(
        EmpresaParceira,
        on_delete=models.PROTECT,  # impede apagar empresa que ainda tem projetos
        related_name='projetos',
        db_column='empresa_id',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANEJAMENTO)
    data_inicio = models.DateField()
    data_fim_prevista = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'projetos'

    def __str__(self):
        return self.nome


class Alocacao(models.Model):
    membro = models.ForeignKey(
        Membro,
        on_delete=models.CASCADE,
        related_name='alocacoes',
        db_column='membro_id',
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name='alocacoes',
        db_column='projeto_id',
    )
    funcao = models.CharField(max_length=60)
    escopo = models.CharField(max_length=60)

    class Meta:
        db_table = 'alocacoes'
        verbose_name = 'Alocação'
        verbose_name_plural = 'Alocações'

    def __str__(self):
        return f'{self.membro.sigla} em {self.projeto.nome} ({self.funcao})'
