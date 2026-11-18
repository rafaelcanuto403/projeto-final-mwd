import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import MAX_MEMBROS_POR_PROJETO, Alocacao, EmpresaParceira, Membro, Projeto

QUANTIDADE_POR_EMPRESA = {
    'CERTI': (6, 152),
    'WEG': (5, 146),
    'Embraco/Nidec': (4, 140),
    'Landis+Gyr': (3, 25),
    'NEO Empresarial': (2, 103),
}

DESCRICOES = [
    'Automação de linha de testes com coleta de dados em tempo real.',
    'Dashboard de indicadores de produção para a equipe de engenharia.',
    'Estudo de viabilidade para redução de consumo energético.',
    'Sistema web para gestão de solicitações internas.',
    'Mapeamento e melhoria de processo produtivo.',
    'Protótipo de sensor IoT para monitoramento de equipamentos.',
    'Análise de dados de qualidade com modelos preditivos.',
    'Aplicativo para controle de inventário de laboratório.',
]


SIGLAS_FORA_DOS_PROJETOS = {'VCE', 'ADU'}

ESCOPOS = Alocacao.Escopo.values


class Command(BaseCommand):
    help = (
        'Cria projetos FICTÍCIOS (W001, L027, ...) e aloca membros já cadastrados neles, '
        'para desenvolvimento do frontend.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpar',
            action='store_true',
            help='Apaga TODOS os projetos (e suas alocações) antes de criar os exemplos.',
        )

    def handle(self, *args, **options):
        rng = random.Random(42)
        hoje = date.today()

        with transaction.atomic():
            if options['limpar']:
                apagados, _ = Projeto.objects.all().delete()
                self.stdout.write(f'{apagados} registros apagados.')
            elif Projeto.objects.exists():
                raise CommandError(
                    'Já existem projetos no banco. Use --limpar para apagá-los e recriar os exemplos.'
                )

            membros = list(
                Membro.objects.exclude(sigla__in=SIGLAS_FORA_DOS_PROJETOS).order_by('sigla')
            )
            if len(membros) < 3:
                self.stdout.write(self.style.WARNING(
                    'Poucos membros cadastrados: rode "importar_membros" antes para criar as alocações.'
                ))

            criados = alocacoes = 0
            for nome_empresa, (quantidade, primeiro_numero) in QUANTIDADE_POR_EMPRESA.items():
                empresa = EmpresaParceira.objects.filter(nome=nome_empresa).first()
                if empresa is None:
                    self.stdout.write(self.style.WARNING(f'Empresa "{nome_empresa}" não encontrada, pulando.'))
                    continue

                inicial = nome_empresa[0].upper()
                for numero in range(1, quantidade + 1):
                    inicio = hoje - timedelta(days=(quantidade - numero) * 120 + rng.randint(10, 60))
                    if numero == quantidade and quantidade >= 4:
                        inicio = hoje + timedelta(days=rng.randint(15, 45))
                    fim = inicio + timedelta(days=rng.choice([90, 120, 180]))
                    if fim < hoje:
                        status = Projeto.Status.CONCLUIDO
                    elif inicio <= hoje:
                        status = Projeto.Status.EM_ANDAMENTO
                    else:
                        status = Projeto.Status.PLANEJAMENTO

                    projeto = Projeto.objects.create(
                        nome=f'{inicial}{primeiro_numero + numero - 1:03d}',
                        descricao=rng.choice(DESCRICOES),
                        empresa=empresa,
                        status=status,
                        data_inicio=inicio,
                        data_fim_prevista=fim,
                    )
                    criados += 1

                    if len(membros) >= MAX_MEMBROS_POR_PROJETO:
                        equipe = rng.sample(membros, k=min(len(membros), rng.randint(2, MAX_MEMBROS_POR_PROJETO)))
                        for indice, membro in enumerate(equipe):
                            Alocacao.objects.create(
                                membro=membro,
                                projeto=projeto,
                                funcao='Gerente de projeto' if indice == 0 else 'Executor',
                                escopo=rng.choice(ESCOPOS),
                            )
                            alocacoes += 1

        self.stdout.write(self.style.SUCCESS(
            f'{criados} projetos de exemplo criados, com {alocacoes} alocações.'
        ))
