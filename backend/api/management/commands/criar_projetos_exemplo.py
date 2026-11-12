import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import EmpresaParceira, Projeto

# Dados FICTÍCIOS para desenvolver o frontend.
# Nome do projeto = inicial da EP + número sequencial (ex.: W1, W2, C1...).
QUANTIDADE_POR_EMPRESA = {
    'CERTI': 6,
    'WEG': 5,
    'Embraco/Nidec': 4,
    'Landis+Gyr': 3,
    'NEO': 2,
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


class Command(BaseCommand):
    help = 'Cria projetos FICTÍCIOS (W1, C1, ...) para desenvolvimento do frontend.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpar',
            action='store_true',
            help='Apaga TODOS os projetos (e suas alocações) antes de criar os exemplos.',
        )

    def handle(self, *args, **options):
        rng = random.Random(42)  # sempre gera os mesmos dados
        hoje = date.today()

        with transaction.atomic():
            if options['limpar']:
                apagados, _ = Projeto.objects.all().delete()
                self.stdout.write(f'{apagados} registros apagados.')
            elif Projeto.objects.exists():
                raise CommandError(
                    'Já existem projetos no banco. Use --limpar para apagá-los e recriar os exemplos.'
                )

            criados = 0
            for nome_empresa, quantidade in QUANTIDADE_POR_EMPRESA.items():
                empresa = EmpresaParceira.objects.filter(nome=nome_empresa).first()
                if empresa is None:
                    self.stdout.write(self.style.WARNING(f'Empresa "{nome_empresa}" não encontrada, pulando.'))
                    continue

                inicial = nome_empresa[0].upper()
                for numero in range(1, quantidade + 1):
                    # Projetos mais antigos tendem a estar concluídos; os mais novos, em andamento/planejamento
                    inicio = hoje - timedelta(days=(quantidade - numero) * 120 + rng.randint(10, 60))
                    if numero == quantidade and quantidade >= 4:
                        # último projeto das EPs maiores ainda vai começar (status "planejamento")
                        inicio = hoje + timedelta(days=rng.randint(15, 45))
                    fim = inicio + timedelta(days=rng.choice([90, 120, 180]))
                    if fim < hoje:
                        status = Projeto.Status.CONCLUIDO
                    elif inicio <= hoje:
                        status = Projeto.Status.EM_ANDAMENTO
                    else:
                        status = Projeto.Status.PLANEJAMENTO

                    Projeto.objects.create(
                        nome=f'{inicial}{numero}',
                        descricao=rng.choice(DESCRICOES),
                        empresa=empresa,
                        status=status,
                        data_inicio=inicio,
                        data_fim_prevista=fim,
                    )
                    criados += 1

        self.stdout.write(self.style.SUCCESS(f'{criados} projetos de exemplo criados.'))
