from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from rest_framework import status
from rest_framework.test import APITestCase

from .management.commands.importar_membros import converter_foto
from .models import Alocacao, EmpresaParceira, Membro, Projeto


class BaseTestCase(APITestCase):
    """Dados mínimos usados pelos testes.

    Obs.: as migrations de dados criam as 5 EPs iniciais (WEG, CERTI...) também no
    banco de testes, por isso os testes criam EPs com nomes próprios.
    """

    def setUp(self):
        self.empresa = EmpresaParceira.objects.create(nome='Empresa Teste', logo_url='/logos/teste.svg')
        self.outra_empresa = EmpresaParceira.objects.create(nome='Outra Empresa')
        self.ana = Membro.objects.create(sigla='ANA', nome='Ana Souza', email='ana@exemplo.com')
        self.bia = Membro.objects.create(sigla='BIA', nome='Bia Lima', email='bia@exemplo.com')
        self.projeto = Projeto.objects.create(
            nome='T1',
            empresa=self.empresa,
            status=Projeto.Status.EM_ANDAMENTO,
            data_inicio=date(2026, 1, 10),
            data_fim_prevista=date(2026, 6, 10),
        )
        self.alocacao = Alocacao.objects.create(
            membro=self.ana, projeto=self.projeto, funcao='Gerente de projeto', escopo='Gestão'
        )


class MigracoesDeDadosTests(APITestCase):
    def test_empresas_iniciais_criadas_com_logos_brancas(self):
        logos = dict(EmpresaParceira.objects.values_list('nome', 'logo_url'))
        self.assertEqual(logos['WEG'], '/logos/weg.svg')
        self.assertEqual(logos['CERTI'], '/logos/certi.svg')
        self.assertEqual(logos['Embraco/Nidec'], '/logos/embraco-nidec.svg')
        self.assertEqual(logos['Landis+Gyr'], '/logos/landis-gyr.svg')
        self.assertEqual(logos['NEO'], '/logos/neo-branco.svg')


class MembroModelTests(APITestCase):
    def test_sigla_precisa_ter_3_letras_maiusculas(self):
        for sigla in ['AB', 'abc', 'A1C', 'ABCD']:
            with self.subTest(sigla=sigla):
                membro = Membro(sigla=sigla, nome='X', email=f'{sigla}@x.com')
                with self.assertRaises(ValidationError):
                    membro.full_clean()

    def test_sigla_valida(self):
        Membro(sigla='XYZ', nome='X', email='xyz@x.com').full_clean()  # não deve lançar erro


class EmpresaApiTests(BaseTestCase):
    def test_lista_traz_total_de_projetos_e_ordena_por_quantidade(self):
        resposta = self.client.get('/api/empresas/')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        primeira = resposta.json()[0]
        self.assertEqual(primeira['nome'], 'Empresa Teste')  # única com projetos
        self.assertEqual(primeira['total_projetos'], 1)

    def test_criar_empresa_retorna_total_zero(self):
        resposta = self.client.post('/api/empresas/', {'nome': 'Nova EP'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.json()['total_projetos'], 0)

    def test_nome_duplicado_tem_mensagem_em_portugues(self):
        resposta = self.client.post('/api/empresas/', {'nome': 'Empresa Teste'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resposta.json()['nome'], ['Já existe uma empresa com este nome.'])

    def test_nao_exclui_empresa_com_projetos(self):
        resposta = self.client.delete(f'/api/empresas/{self.empresa.id}/')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('projetos vinculados', resposta.json()['detail'])
        self.assertTrue(EmpresaParceira.objects.filter(id=self.empresa.id).exists())

    def test_exclui_empresa_sem_projetos(self):
        resposta = self.client.delete(f'/api/empresas/{self.outra_empresa.id}/')
        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)


class ProjetoApiTests(BaseTestCase):
    def dados(self, **extra):
        return {
            'nome': 'T2',
            'empresa': self.empresa.id,
            'status': 'planejamento',
            'data_inicio': '2026-03-01',
            **extra,
        }

    def test_filtra_por_empresa(self):
        Projeto.objects.create(nome='O1', empresa=self.outra_empresa, data_inicio=date(2026, 1, 1))
        resposta = self.client.get(f'/api/projetos/?empresa={self.empresa.id}')
        self.assertEqual([p['nome'] for p in resposta.json()], ['T1'])

    def test_filtro_de_empresa_invalido(self):
        resposta = self.client.get('/api/projetos/?empresa=abc')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_traz_campos_de_exibicao(self):
        projeto = self.client.get(f'/api/projetos/{self.projeto.id}/').json()
        self.assertEqual(projeto['empresa_nome'], 'Empresa Teste')
        self.assertEqual(projeto['empresa_logo_url'], '/logos/teste.svg')
        self.assertEqual(projeto['status_display'], 'Em andamento')

    def test_status_padrao_e_planejamento(self):
        dados = self.dados()
        del dados['status']
        resposta = self.client.post('/api/projetos/', dados, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.json()['status'], 'planejamento')

    def test_fim_antes_do_inicio_e_recusado(self):
        resposta = self.client.post('/api/projetos/', self.dados(data_fim_prevista='2026-02-01'), format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_fim_prevista', resposta.json())

    def test_edicao_parcial_tambem_valida_datas(self):
        # Só a data de fim é enviada; o início (10/01) vem do projeto já salvo
        resposta = self.client.patch(
            f'/api/projetos/{self.projeto.id}/', {'data_fim_prevista': '2025-12-31'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_status_invalido_e_recusado(self):
        resposta = self.client.post('/api/projetos/', self.dados(status='pausado'), format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_excluir_projeto_remove_alocacoes(self):
        self.client.delete(f'/api/projetos/{self.projeto.id}/')
        self.assertFalse(Alocacao.objects.filter(id=self.alocacao.id).exists())


class MembroApiTests(BaseTestCase):
    def test_normaliza_sigla_e_email(self):
        resposta = self.client.post(
            '/api/membros/', {'sigla': ' cdx ', 'nome': 'Carla', 'email': ' CARLA@Exemplo.com'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.json()['sigla'], 'CDX')
        self.assertEqual(resposta.json()['email'], 'carla@exemplo.com')

    def test_sigla_duplicada_mesmo_em_minusculas(self):
        resposta = self.client.post(
            '/api/membros/', {'sigla': 'ana', 'nome': 'Outra Ana', 'email': 'outra@exemplo.com'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resposta.json()['sigla'], ['Já existe um membro com esta sigla.'])

    def test_email_duplicado(self):
        resposta = self.client.post(
            '/api/membros/', {'sigla': 'NOV', 'nome': 'Nova', 'email': 'ANA@exemplo.com'}, format='json'
        )
        self.assertEqual(resposta.json()['email'], ['Já existe um membro com este e-mail.'])

    def test_email_invalido(self):
        resposta = self.client.post(
            '/api/membros/', {'sigla': 'NOV', 'nome': 'Nova', 'email': 'nao-e-email'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resposta.json())

    def test_total_de_projetos_conta_cada_projeto_uma_vez(self):
        # Ana com duas funções no mesmo projeto continua com 1 projeto
        Alocacao.objects.create(membro=self.ana, projeto=self.projeto, funcao='Executor', escopo='Dados')
        membros = {m['sigla']: m for m in self.client.get('/api/membros/').json()}
        self.assertEqual(membros['ANA']['total_projetos'], 1)
        self.assertEqual(membros['BIA']['total_projetos'], 0)

    def test_excluir_membro_remove_alocacoes(self):
        self.client.delete(f'/api/membros/{self.ana.id}/')
        self.assertFalse(Alocacao.objects.filter(id=self.alocacao.id).exists())


class AlocacaoApiTests(BaseTestCase):
    def test_filtra_por_projeto_e_por_membro(self):
        outro = Projeto.objects.create(nome='T9', empresa=self.empresa, data_inicio=date(2026, 2, 1))
        Alocacao.objects.create(membro=self.bia, projeto=outro, funcao='Executor', escopo='Dados')

        por_projeto = self.client.get(f'/api/alocacoes/?projeto={self.projeto.id}').json()
        self.assertEqual([a['membro_sigla'] for a in por_projeto], ['ANA'])

        por_membro = self.client.get(f'/api/alocacoes/?membro={self.bia.id}').json()
        self.assertEqual([a['projeto_nome'] for a in por_membro], ['T9'])

    def test_filtro_invalido(self):
        self.assertEqual(self.client.get('/api/alocacoes/?membro=x').status_code, status.HTTP_400_BAD_REQUEST)

    def test_traz_dados_do_membro_projeto_e_empresa(self):
        alocacao = self.client.get(f'/api/alocacoes/{self.alocacao.id}/').json()
        self.assertEqual(alocacao['membro_nome'], 'Ana Souza')
        self.assertEqual(alocacao['projeto_status_display'], 'Em andamento')
        self.assertEqual(alocacao['empresa_nome'], 'Empresa Teste')

    def test_criar_alocacao_exige_funcao_e_escopo(self):
        resposta = self.client.post(
            '/api/alocacoes/', {'membro': self.bia.id, 'projeto': self.projeto.id}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('funcao', resposta.json())
        self.assertIn('escopo', resposta.json())


class ImportarMembrosTests(APITestCase):
    USUARIOS = [
        {
            'username': 'abc', 'firstName': 'Ana', 'lastName': ' Beatriz  Costa', 'email': 'ABC@x.com',
            'isActivate': True, 'pictureUrl': None,
            'drivePhotoUrl': 'https://drive.google.com/file/d/ID_123/view?usp=drive_link',
        },
        {
            'username': 'DEF', 'firstName': 'Davi', 'lastName': 'Ferreira', 'email': 'def@x.com',
            'isActivate': False, 'pictureUrl': None, 'drivePhotoUrl': None,
        },
    ]

    def test_converter_foto(self):
        self.assertEqual(converter_foto({'pictureUrl': 'https://foto'}), 'https://foto')
        self.assertEqual(
            converter_foto({'drivePhotoUrl': 'https://drive.google.com/file/d/ABC-1/view'}),
            'https://drive.google.com/thumbnail?id=ABC-1&sz=w400',
        )
        self.assertIsNone(converter_foto({}))

    def importar(self, *args):
        with patch('api.management.commands.importar_membros.urlopen') as urlopen, \
             patch('api.management.commands.importar_membros.json.load', return_value=self.USUARIOS):
            urlopen.return_value.__enter__.return_value = StringIO()
            call_command('importar_membros', *args, stdout=StringIO())

    def test_importa_so_ativos_normalizando_dados(self):
        self.importar()
        membro = Membro.objects.get()
        self.assertEqual(membro.sigla, 'ABC')
        self.assertEqual(membro.nome, 'Ana Beatriz Costa')
        self.assertEqual(membro.email, 'abc@x.com')
        self.assertEqual(membro.foto_url, 'https://drive.google.com/thumbnail?id=ID_123&sz=w400')

    def test_todos_inclui_inativos_e_rodar_de_novo_nao_duplica(self):
        self.importar('--todos')
        self.importar('--todos')
        self.assertEqual(Membro.objects.count(), 2)


class ProjetosExemploTests(APITestCase):
    def test_cria_projetos_numerados_e_alocacoes(self):
        for i, sigla in enumerate(['AAA', 'BBB', 'CCC', 'DDD', 'EEE']):
            Membro.objects.create(sigla=sigla, nome=f'Membro {i}', email=f'{sigla}@x.com')
        call_command('criar_projetos_exemplo', stdout=StringIO())

        nomes = set(Projeto.objects.values_list('nome', flat=True))
        self.assertEqual(Projeto.objects.count(), 20)
        self.assertTrue({'C152', 'C157', 'W1', 'E143', 'N103', 'L3'} <= nomes)
        self.assertTrue(Alocacao.objects.exists())

    def test_recusa_rodar_com_projetos_existentes(self):
        empresa = EmpresaParceira.objects.get(nome='WEG')
        Projeto.objects.create(nome='X1', empresa=empresa, data_inicio=date(2026, 1, 1))
        with self.assertRaises(CommandError):
            call_command('criar_projetos_exemplo', stdout=StringIO())
