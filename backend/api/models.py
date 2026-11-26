from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.db.models.signals import post_delete
from django.dispatch import receiver


class EmpresaParceira(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    logo_url = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'empresas_parceiras'
        verbose_name = 'Empresa parceira'
        verbose_name_plural = 'Empresas parceiras'

    def __str__(self):
        return self.nome


# Regra interna do NEO: os cargos mudam a cada semestre e cada um é ocupado por um único
# membro. Só estes podem ser de vários membros ao mesmo tempo:
CARGOS_REPETIVEIS = ['Executor Pleno', 'Calouro']
# O AG PRJ é o Admin do sistema.
CARGO_ADMIN = 'AG PRJ'


def normalizar_cargo(cargo):
    """Junta espaços e padroniza a grafia dos cargos conhecidos ("ag  prj" -> "AG PRJ")."""
    cargo = ' '.join((cargo or '').split())
    for conhecido in [CARGO_ADMIN, *CARGOS_REPETIVEIS]:
        if cargo.lower() == conhecido.lower():
            return conhecido
    return cargo


def eh_cargo_admin(cargo):
    return normalizar_cargo(cargo) == CARGO_ADMIN


def eh_cargo_unico(cargo):
    cargo = normalizar_cargo(cargo)
    return bool(cargo) and cargo not in CARGOS_REPETIVEIS


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
    cargo = models.CharField(max_length=80, blank=True, default='')
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='membro',
        db_column='user_id',
    )

    class Meta:
        db_table = 'membros'
        constraints = [
            # Cargo único (sem diferenciar maiúsculas), exceto "sem cargo" e os repetíveis.
            models.UniqueConstraint(
                Lower('cargo'),
                condition=~models.Q(cargo__in=['', *CARGOS_REPETIVEIS]),
                name='cargo_unico',
                violation_error_message='Este cargo já é ocupado por outro membro.',
            ),
        ]

    def __str__(self):
        return f'{self.sigla} - {self.nome}'

    def save(self, *args, **kwargs):
        # A grafia padronizada é o que faz a constraint de cargo único valer.
        self.cargo = normalizar_cargo(self.cargo)
        super().save(*args, **kwargs)


class Projeto(models.Model):
    class Status(models.TextChoices):
        PLANEJAMENTO = 'planejamento', 'Planejamento'
        EM_ANDAMENTO = 'em_andamento', 'Em andamento'
        CONCLUIDO = 'concluido', 'Concluído'

    nome = models.CharField(max_length=150)
    descricao = models.CharField(max_length=500, blank=True, null=True)
    empresa = models.ForeignKey(
        EmpresaParceira,
        on_delete=models.PROTECT,
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


MAX_MEMBROS_POR_PROJETO = 3


class Alocacao(models.Model):
    class Funcao(models.TextChoices):
        # A função dá permissões no projeto (ver api/permissoes.py), por isso é uma lista fechada.
        GERENTE_DE_PROJETO = 'Gerente de projeto', 'Gerente de projeto'
        EXECUTOR = 'Executor', 'Executor'

    class Escopo(models.TextChoices):
        WEB = 'Web', 'Web'
        DATA_SCIENCE = 'Data Science', 'Data Science'
        BUSINESS_INTELLIGENCE = 'Business Intelligence', 'Business Intelligence'
        VISAO_COMPUTACIONAL = 'Visão Computacional', 'Visão Computacional'
        AI = 'AI', 'AI'

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
    funcao = models.CharField(max_length=60, choices=Funcao.choices)
    escopo = models.CharField(max_length=60, choices=Escopo.choices)

    class Meta:
        db_table = 'alocacoes'
        verbose_name = 'Alocação'
        verbose_name_plural = 'Alocações'
        constraints = [
            models.UniqueConstraint(
                fields=['projeto'],
                condition=models.Q(funcao='Gerente de projeto'),
                name='um_gerente_por_projeto',
                violation_error_message='Este projeto já tem um gerente.',
            ),
        ]

    def __str__(self):
        return f'{self.membro.sigla} em {self.projeto.nome} ({self.funcao})'


class Documento(models.Model):
    class Tipo(models.TextChoices):
        ABERTURA = 'abertura', 'Documento de abertura'
        CONTRATO = 'contrato', 'Contrato'
        PROPOSTA = 'proposta', 'Proposta'
        RELATORIO = 'relatorio', 'Relatório'
        ATA = 'ata', 'Ata de reunião'
        OUTRO = 'outro', 'Outro'

    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name='documentos',
        db_column='projeto_id',
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.OUTRO)
    titulo = models.CharField(max_length=150)
    arquivo = models.FileField(upload_to='documentos/%Y/%m/')
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documentos'
        ordering = ['-enviado_em']

    def __str__(self):
        return f'{self.titulo} ({self.projeto.nome})'


@receiver(post_delete, sender=Documento)
def apagar_arquivo_do_documento(sender, instance, **kwargs):
    from .previas import apagar_previas

    instance.arquivo.delete(save=False)
    apagar_previas(instance.pk)


@receiver(post_delete, sender=Membro)
def apagar_usuario_do_membro(sender, instance, **kwargs):
    if instance.user_id:
        instance.user.delete()
