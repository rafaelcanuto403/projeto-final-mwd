import shutil
import tempfile
from datetime import date
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.db import IntegrityError, transaction
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .management.commands.importar_membros import converter_foto
from .models import Alocacao, Documento, EmpresaParceira, Membro, Projeto
from .permissoes import ADMIN, MEMBRO, papel_de
from .serializers import sincronizar_usuario


HASH_RAPIDO = override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])


@HASH_RAPIDO
class BaseTestCase(APITestCase):
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
            membro=self.ana, projeto=self.projeto, funcao='Gerente de projeto', escopo='Web'
        )
        self.admin = Membro.objects.create(
            sigla='ADM', nome='Admin Teste', email='adm@exemplo.com', cargo='AG PRJ'
        )
        self.client.force_authenticate(sincronizar_usuario(self.admin, senha='Senha-Forte-123'))


class MigracoesDeDadosTests(APITestCase):
    def test_empresas_iniciais_criadas_com_logos_brancas(self):
        logos = dict(EmpresaParceira.objects.values_list('nome', 'logo_url'))
        self.assertEqual(logos['WEG'], '/logos/weg.svg')
        self.assertEqual(logos['CERTI'], '/logos/certi.svg')
        self.assertEqual(logos['Embraco/Nidec'], '/logos/embraco-nidec.svg')
        self.assertEqual(logos['Landis+Gyr'], '/logos/landis-gyr.svg')
        self.assertEqual(logos['NEO Empresarial'], '/logos/neo-branco.svg')
        self.assertNotIn('NEO', logos)
        self.assertEqual(logos['Comerc Energia'], '/logos/comerc-energia.svg')


class MembroModelTests(APITestCase):
    def test_sigla_precisa_ter_3_letras_maiusculas(self):
        for sigla in ['AB', 'abc', 'A1C', 'ABCD']:
            with self.subTest(sigla=sigla):
                membro = Membro(sigla=sigla, nome='X', email=f'{sigla}@x.com')
                with self.assertRaises(ValidationError):
                    membro.full_clean()

    def test_sigla_valida(self):
        Membro(sigla='XYZ', nome='X', email='xyz@x.com').full_clean()


class EmpresaApiTests(BaseTestCase):
    def test_lista_traz_total_de_projetos_e_ordena_por_quantidade(self):
        resposta = self.client.get('/api/empresas/')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        primeira = resposta.json()[0]
        self.assertEqual(primeira['nome'], 'Empresa Teste')
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
        Alocacao.objects.create(membro=self.ana, projeto=self.projeto, funcao='Executor', escopo='Data Science')
        membros = {m['sigla']: m for m in self.client.get('/api/membros/').json()}
        self.assertEqual(membros['ANA']['total_projetos'], 1)
        self.assertEqual(membros['BIA']['total_projetos'], 0)

    def test_excluir_membro_remove_alocacoes(self):
        self.client.delete(f'/api/membros/{self.ana.id}/')
        self.assertFalse(Alocacao.objects.filter(id=self.alocacao.id).exists())


class AlocacaoApiTests(BaseTestCase):
    def test_filtra_por_projeto_e_por_membro(self):
        outro = Projeto.objects.create(nome='T9', empresa=self.empresa, data_inicio=date(2026, 2, 1))
        Alocacao.objects.create(membro=self.bia, projeto=outro, funcao='Executor', escopo='Data Science')

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

    def test_escopo_so_aceita_valores_da_lista(self):
        url = f'/api/alocacoes/{self.alocacao.id}/'
        resposta = self.client.patch(url, {'escopo': 'Hardware'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Visão Computacional', resposta.json()['escopo'][0])

        resposta = self.client.patch(url, {'escopo': 'Business Intelligence'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_equipe_tem_no_maximo_3_membros(self):
        for sigla in ['BBB', 'CCC']:
            membro = Membro.objects.create(sigla=sigla, nome=sigla, email=f'{sigla}@x.com')
            Alocacao.objects.create(membro=membro, projeto=self.projeto, funcao='Executor', escopo='Data Science')

        resposta = self.client.post(
            '/api/alocacoes/',
            {'membro': self.bia.id, 'projeto': self.projeto.id, 'funcao': 'Executor', 'escopo': 'Data Science'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('máximo', resposta.json()['non_field_errors'][0])

        resposta = self.client.patch(f'/api/alocacoes/{self.alocacao.id}/', {'escopo': 'AI'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)


PASTA_MEDIA_TESTES = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=PASTA_MEDIA_TESTES)
class DocumentoApiTests(BaseTestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(PASTA_MEDIA_TESTES, ignore_errors=True)
        super().tearDownClass()

    def enviar(self, nome='Abertura C1.pdf', conteudo=b'%PDF-1.4 teste', **campos):
        dados = {'projeto': self.projeto.id, 'tipo': 'abertura', **campos}
        dados['arquivo'] = SimpleUploadedFile(nome, conteudo)
        return self.client.post('/api/documentos/', dados, format='multipart')

    def test_upload_lista_por_projeto_e_titulo_padrao(self):
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED, resposta.json())
        documento = resposta.json()
        self.assertEqual(documento['titulo'], 'Abertura C1')
        self.assertEqual(documento['tipo_display'], 'Documento de abertura')
        self.assertNotIn('arquivo_url', documento)
        self.assertEqual(documento['nome_arquivo'], 'Abertura_C1.pdf')
        self.assertEqual(documento['tamanho'], len(b'%PDF-1.4 teste'))

        outro = Projeto.objects.create(nome='T2', empresa=self.empresa, data_inicio=date(2026, 3, 1))
        self.client.post(
            '/api/documentos/',
            {'projeto': outro.id, 'tipo': 'contrato', 'titulo': 'Contrato',
             'arquivo': SimpleUploadedFile('c.pdf', b'x')},
            format='multipart',
        )
        do_projeto = self.client.get(f'/api/documentos/?projeto={self.projeto.id}').json()
        self.assertEqual([d['titulo'] for d in do_projeto], ['Abertura C1'])

    def test_recusa_formato_nao_aceito(self):
        resposta = self.enviar(nome='script.exe')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Formato não aceito', resposta.json()['arquivo'][0])

    def test_recusa_arquivo_maior_que_20_mb(self):
        with patch('api.serializers.TAMANHO_MAXIMO_DOCUMENTO', 10):
            resposta = self.enviar(conteudo=b'x' * 11)
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('20 MB', resposta.json()['arquivo'][0])

    def test_excluir_apaga_o_arquivo_do_disco(self):
        documento = self.enviar(titulo='Contrato').json()
        caminho = Path(PASTA_MEDIA_TESTES) / Documento.objects.get(id=documento['id']).arquivo.name
        self.assertTrue(caminho.exists())

        resposta = self.client.delete(f'/api/documentos/{documento["id"]}/')
        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(caminho.exists())

    def test_excluir_projeto_remove_os_documentos_e_arquivos(self):
        documento = self.enviar().json()
        caminho = Path(PASTA_MEDIA_TESTES) / Documento.objects.get(id=documento['id']).arquivo.name
        self.projeto.delete()
        self.assertFalse(Documento.objects.exists())
        self.assertFalse(caminho.exists())


class ImportarMembrosTests(APITestCase):
    USUARIOS = [
        {
            'username': 'abc', 'firstName': 'Ana', 'lastName': ' Beatriz  Costa', 'email': 'ABC@x.com',
            'isActivate': True, 'pictureUrl': None, 'role': ' Executor  Pleno ',
            'drivePhotoUrl': 'https://drive.google.com/file/d/ID_123/view?usp=drive_link',
        },
        {
            'username': 'DEF', 'firstName': 'Davi', 'lastName': 'Ferreira', 'email': 'def@x.com',
            'isActivate': False, 'pictureUrl': None, 'drivePhotoUrl': None, 'role': None,
        },
    ]

    def test_converter_foto(self):
        self.assertEqual(converter_foto({'pictureUrl': 'https://foto'}), 'https://foto')
        self.assertEqual(
            converter_foto({'drivePhotoUrl': 'https://drive.google.com/file/d/ABC-1/view'}),
            'https://drive.google.com/thumbnail?id=ABC-1&sz=w400',
        )
        self.assertIsNone(converter_foto({}))

    def test_foto_local_tem_prioridade_sobre_a_da_api(self):
        from .management.commands.importar_membros import PASTA_FOTOS_LOCAIS, foto_do_membro

        sigla = next(PASTA_FOTOS_LOCAIS.glob('*.webp')).stem
        usuario = {'username': sigla.upper(), 'pictureUrl': 'https://foto-da-api'}
        self.assertEqual(foto_do_membro(usuario), f'/membros/{sigla}.webp')
        self.assertEqual(foto_do_membro({'username': 'ZZZ', 'pictureUrl': 'https://foto-da-api'}), 'https://foto-da-api')

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
        self.assertEqual(membro.cargo, 'Executor Pleno')

    def test_todos_inclui_inativos_e_rodar_de_novo_nao_duplica(self):
        self.importar('--todos')
        self.importar('--todos')
        self.assertEqual(Membro.objects.count(), 2)
        self.assertEqual(Membro.objects.get(sigla='DEF').cargo, '')

    def test_troca_de_semestre_faz_rodizio_dos_cargos(self):
        Membro.objects.create(sigla='ABC', nome='A', email='abc@x.com', cargo='AG DP')
        Membro.objects.create(sigla='DEF', nome='D', email='def@x.com', cargo='AG MKT')
        Membro.objects.create(sigla='GHI', nome='G', email='ghi@x.com', cargo='AG LID')  # saiu da API
        novo_semestre = [
            {**self.USUARIOS[0], 'role': 'AG MKT'},
            {**self.USUARIOS[1], 'isActivate': True, 'role': 'ag  lid'},
            {'username': 'JKL', 'firstName': 'J', 'lastName': 'K', 'email': 'jkl@x.com',
             'isActivate': True, 'pictureUrl': None, 'role': 'AG DP'},
        ]
        with patch.object(self, 'USUARIOS', novo_semestre):
            self.importar()
        cargos = dict(Membro.objects.values_list('sigla', 'cargo'))
        self.assertEqual(cargos, {'ABC': 'AG MKT', 'DEF': 'ag lid', 'GHI': '', 'JKL': 'AG DP'})


class ProjetosExemploTests(APITestCase):
    def test_cria_projetos_numerados_e_alocacoes(self):
        for i, sigla in enumerate(['AAA', 'BBB', 'CCC', 'DDD', 'EEE']):
            Membro.objects.create(sigla=sigla, nome=f'Membro {i}', email=f'{sigla}@x.com')
        call_command('criar_projetos_exemplo', stdout=StringIO())

        nomes = set(Projeto.objects.values_list('nome', flat=True))
        self.assertEqual(Projeto.objects.count(), 20)
        self.assertTrue({'C152', 'C157', 'W146', 'W150', 'E143', 'N103', 'L025', 'L027'} <= nomes)
        self.assertTrue(Alocacao.objects.exists())
        escopos = set(Alocacao.objects.values_list('escopo', flat=True))
        self.assertTrue(escopos <= set(Alocacao.Escopo.values))
        maior_equipe = max(p.alocacoes.count() for p in Projeto.objects.all())
        self.assertLessEqual(maior_equipe, 3)

    def test_cargos_gerenciais_nao_entram_nas_equipes(self):
        for i, sigla in enumerate(['AAA', 'BBB', 'CCC', 'VCE', 'ADU']):
            Membro.objects.create(sigla=sigla, nome=f'Membro {i}', email=f'{sigla}@x.com')
        call_command('criar_projetos_exemplo', stdout=StringIO())

        self.assertTrue(Alocacao.objects.exists())
        self.assertFalse(Alocacao.objects.filter(membro__sigla__in=['VCE', 'ADU']).exists())

    def test_recusa_rodar_com_projetos_existentes(self):
        empresa = EmpresaParceira.objects.get(nome='WEG')
        Projeto.objects.create(nome='X1', empresa=empresa, data_inicio=date(2026, 1, 1))
        with self.assertRaises(CommandError):
            call_command('criar_projetos_exemplo', stdout=StringIO())


# ---- controle de acesso (RBAC + ABAC) --------------------------------------

class AcessoBaseTestCase(BaseTestCase):
    """No projeto T1: Ana = gerente do projeto, Edu = executor. Bia = fora do projeto. ADM = admin."""

    def setUp(self):
        super().setUp()
        self.user_ana = sincronizar_usuario(self.ana, 'Senha-Forte-123')
        self.user_bia = sincronizar_usuario(self.bia, 'Senha-Forte-123')
        self.edu = Membro.objects.create(sigla='EDU', nome='Edu Executor', email='edu@exemplo.com')
        self.user_edu = sincronizar_usuario(self.edu, 'Senha-Forte-123')
        Alocacao.objects.create(membro=self.edu, projeto=self.projeto, funcao='Executor', escopo='Web')
        self.user_admin = self.admin.user

    def como(self, user):
        self.client.force_authenticate(get_user_model().objects.get(pk=user.pk))  # sem cache de papel

    def concluir_projeto(self):
        self.projeto.status = Projeto.Status.CONCLUIDO
        self.projeto.save()


class AutenticacaoTests(AcessoBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(None)

    def login(self, email='ana@exemplo.com', senha='Senha-Forte-123'):
        return self.client.post('/api/auth/login/', {'email': email, 'senha': senha}, format='json')

    def test_sem_token_recebe_401(self):
        for url in ['/api/empresas/', '/api/projetos/', '/api/membros/', '/api/auth/me/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_com_email_em_maiusculas_e_uso_do_token(self):
        resposta = self.login(email='ANA@Exemplo.com')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        tokens = resposta.json()
        self.assertIn('refresh', tokens)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        me = self.client.get('/api/auth/me/').json()
        self.assertEqual(me['papel'], MEMBRO)
        self.assertEqual(me['membro']['sigla'], 'ANA')
        self.assertFalse(me['permissoes']['empresa']['criar'])
        self.assertFalse(me['permissoes']['projeto']['criar'])

    def test_refresh_gera_novo_access(self):
        refresh = self.login().json()['refresh']
        resposta = self.client.post('/api/auth/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn('access', resposta.json())

    def test_senha_errada(self):
        resposta = self.login(senha='errada')
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resposta.json()['detail'], 'E-mail ou senha incorretos.')

    def test_usuario_desativado_nao_entra_e_perde_o_token_na_hora(self):
        access = self.login().json()['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(self.client.get('/api/projetos/').status_code, status.HTTP_200_OK)

        self.user_ana.is_active = False
        self.user_ana.save()
        self.assertIn(self.client.get('/api/projetos/').status_code, {401, 403})
        self.client.credentials()
        self.assertEqual(self.login().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_superusuario_e_usuario_sem_membro_nao_tem_acesso(self):
        User = get_user_model()
        root = User.objects.create_superuser('root', 'root@exemplo.com', 'Senha-Forte-123')
        solto = User.objects.create_user('solto@exemplo.com', 'solto@exemplo.com', 'Senha-Forte-123')
        for user in [root, solto]:
            self.como(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get('/api/projetos/').status_code, status.HTTP_403_FORBIDDEN)

    def test_media_nao_e_servida_publicamente(self):
        self.assertEqual(
            self.client.get('/media/documentos/qualquer.pdf').status_code, status.HTTP_404_NOT_FOUND
        )


class PapelTests(AcessoBaseTestCase):
    def test_so_existem_admin_e_membro_e_ninguem_escolhe_papel(self):
        self.assertEqual(papel_de(self.user_admin), ADMIN)
        for user in [self.user_ana, self.user_edu, self.user_bia]:
            self.assertEqual(papel_de(user), MEMBRO)

        # "papel" é só leitura: enviá-lo não muda nada.
        resposta = self.client.patch(f'/api/membros/{self.bia.id}/', {'papel': ADMIN}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.json()['papel'], MEMBRO)

    def test_me_do_admin_libera_criar_projeto(self):
        self.como(self.user_admin)
        me = self.client.get('/api/auth/me/').json()
        self.assertEqual(me['papel'], ADMIN)
        self.assertTrue(me['permissoes']['projeto']['criar'])


class EmpresaAcessoTests(AcessoBaseTestCase):
    def test_so_admin_cria_edita_e_exclui(self):
        url = f'/api/empresas/{self.outra_empresa.id}/'
        for user in [self.user_ana, self.user_edu]:
            self.como(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get('/api/empresas/').status_code, status.HTTP_200_OK)
                criar = self.client.post('/api/empresas/', {'nome': 'X'}, format='json')
                self.assertEqual(criar.status_code, status.HTTP_403_FORBIDDEN)
                editar = self.client.patch(url, {'nome': 'Y'}, format='json')
                self.assertEqual(editar.status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN)


class MembroAcessoTests(AcessoBaseTestCase):
    def test_membro_edita_nome_do_proprio_perfil(self):
        self.como(self.user_edu)
        resposta = self.client.patch(f'/api/membros/{self.edu.id}/', {'nome': 'Edu S.'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.json()['nome'], 'Edu S.')

    def test_membro_pode_reenviar_o_formulario_inteiro_sem_mudar_campos_restritos(self):
        self.como(self.user_ana)
        dados = self.client.get(f'/api/membros/{self.ana.id}/').json()
        dados['nome'] = 'Ana Nova'
        campos = ['sigla', 'nome', 'email', 'foto_url', 'cargo', 'papel']
        resposta = self.client.put(
            f'/api/membros/{self.ana.id}/', {k: dados[k] for k in campos}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK, resposta.json())

    def test_membro_nao_altera_cargo_nem_sigla_proprios(self):
        self.como(self.user_ana)
        for campo, valor in [('cargo', 'Diretora'), ('sigla', 'ANN'), ('email', 'outro@exemplo.com')]:
            with self.subTest(campo=campo):
                resposta = self.client.patch(f'/api/membros/{self.ana.id}/', {campo: valor}, format='json')
                self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.cargo, '')

    def test_gerente_de_projeto_e_membro_nao_editam_outro_membro(self):
        for user in [self.user_ana, self.user_edu]:
            self.como(user)
            resposta = self.client.patch(f'/api/membros/{self.bia.id}/', {'nome': 'X'}, format='json')
            self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_so_admin_cria_e_exclui_membro(self):
        self.como(self.user_ana)
        dados = {'sigla': 'NOV', 'nome': 'Novo', 'email': 'novo@exemplo.com'}
        self.assertEqual(
            self.client.post('/api/membros/', dados, format='json').status_code, status.HTTP_403_FORBIDDEN
        )
        self.assertEqual(
            self.client.delete(f'/api/membros/{self.bia.id}/').status_code, status.HTTP_403_FORBIDDEN
        )

    def test_admin_cria_membro_com_senha_e_ele_consegue_entrar(self):
        dados = {'sigla': 'NOV', 'nome': 'Novo', 'email': 'novo@exemplo.com', 'senha': 'Outra-Senha-456'}
        resposta = self.client.post('/api/membros/', dados, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED, resposta.json())
        self.assertEqual(resposta.json()['papel'], MEMBRO)
        self.assertTrue(resposta.json()['tem_acesso'])
        self.assertNotIn('senha', resposta.json())

        self.client.force_authenticate(None)
        login = self.client.post(
            '/api/auth/login/', {'email': 'novo@exemplo.com', 'senha': 'Outra-Senha-456'}, format='json'
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_membro_criado_sem_senha_fica_sem_acesso(self):
        dados = {'sigla': 'NOV', 'nome': 'Novo', 'email': 'novo@exemplo.com'}
        resposta = self.client.post('/api/membros/', dados, format='json')
        self.assertFalse(resposta.json()['tem_acesso'])

    def test_senha_fraca_e_recusada(self):
        resposta = self.client.patch(f'/api/membros/{self.bia.id}/', {'senha': '123'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('senha', resposta.json())

    def test_admin_nao_deixa_o_proprio_cargo_ag_prj_nem_se_exclui(self):
        url = f'/api/membros/{self.admin.id}/'
        resposta = self.client.patch(url, {'cargo': 'Executor Pleno'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('AG PRJ', resposta.json()['cargo'][0])
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_400_BAD_REQUEST)

    def test_passar_o_cargo_ag_prj_transfere_o_admin(self):
        resposta = self.client.patch(f'/api/membros/{self.bia.id}/', {'cargo': ' ag  prj '}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK, resposta.json())
        self.assertEqual(resposta.json()['cargo'], 'AG PRJ')
        self.assertEqual(resposta.json()['papel'], ADMIN)

        self.admin.refresh_from_db()
        self.assertEqual(self.admin.cargo, '')
        self.assertEqual(Membro.objects.filter(cargo='AG PRJ').count(), 1)

        # O antigo AG PRJ perde o Admin na hora; a nova AG PRJ ganha.
        self.como(self.user_admin)
        self.assertEqual(
            self.client.post('/api/empresas/', {'nome': 'EP X'}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.como(self.user_bia)
        self.assertEqual(
            self.client.post('/api/empresas/', {'nome': 'EP da Bia'}, format='json').status_code,
            status.HTTP_201_CREATED,
        )

    def test_novo_membro_ag_prj_tambem_recebe_o_cargo_por_passagem(self):
        dados = {'sigla': 'NOV', 'nome': 'Novo', 'email': 'novo@exemplo.com', 'cargo': 'AG PRJ'}
        resposta = self.client.post('/api/membros/', dados, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED, resposta.json())
        self.assertEqual(list(Membro.objects.filter(cargo='AG PRJ').values_list('sigla', flat=True)), ['NOV'])

    def test_banco_nao_aceita_dois_ag_prj(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Membro.objects.create(sigla='DUP', nome='Dup', email='dup@exemplo.com', cargo='ag prj')

    def test_excluir_membro_apaga_o_login(self):
        user_id = self.user_bia.id
        self.client.delete(f'/api/membros/{self.bia.id}/')
        self.assertFalse(get_user_model().objects.filter(id=user_id).exists())


class CargoUnicoTests(AcessoBaseTestCase):
    def test_cargo_unico_sem_diferenciar_maiusculas_no_banco(self):
        Membro.objects.create(sigla='TES', nome='T', email='t@x.com', cargo='Tesoureiro')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Membro.objects.create(sigla='TSR', nome='T2', email='t2@x.com', cargo='tesoureiro')

    def test_executor_pleno_calouro_e_sem_cargo_podem_repetir(self):
        for i, cargo in enumerate(['Executor Pleno', 'executor  pleno', 'Calouro', 'CALOURO', '', '']):
            Membro.objects.create(sigla=f'R{chr(65 + i)}X', nome='R', email=f'r{i}@x.com', cargo=cargo)
        self.assertEqual(Membro.objects.filter(cargo='Executor Pleno').count(), 2)
        self.assertEqual(Membro.objects.filter(cargo='Calouro').count(), 2)

    def test_dar_um_cargo_ocupado_passa_o_cargo(self):
        dono = Membro.objects.create(sigla='DON', nome='Dono', email='dono@x.com', cargo='AG DP')
        resposta = self.client.patch(f'/api/membros/{self.bia.id}/', {'cargo': 'ag dp'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK, resposta.json())
        dono.refresh_from_db()
        self.assertEqual(dono.cargo, '')
        self.assertEqual(list(Membro.objects.filter(cargo__iexact='ag dp').values_list('sigla', flat=True)), ['BIA'])

    def test_dar_cargo_repetivel_nao_tira_de_ninguem(self):
        outro = Membro.objects.create(sigla='EXP', nome='Exp', email='exp@x.com', cargo='Executor Pleno')
        self.client.patch(f'/api/membros/{self.bia.id}/', {'cargo': 'Executor Pleno'}, format='json')
        outro.refresh_from_db()
        self.assertEqual(outro.cargo, 'Executor Pleno')


class ProjetoAcessoTests(AcessoBaseTestCase):
    def novo_projeto(self):
        return {'nome': 'T9', 'empresa': self.empresa.id, 'data_inicio': '2026-02-01'}

    def url(self):
        return f'/api/projetos/{self.projeto.id}/'

    def test_so_admin_cria_e_exclui_projetos(self):
        for user in [self.user_ana, self.user_edu, self.user_bia]:
            self.como(user)
            with self.subTest(user=user.username):
                criar = self.client.post('/api/projetos/', self.novo_projeto(), format='json')
                self.assertEqual(criar.status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(self.client.delete(self.url()).status_code, status.HTTP_403_FORBIDDEN)
        self.como(self.user_admin)
        resposta = self.client.post('/api/projetos/', self.novo_projeto(), format='json')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)

    def test_so_o_gerente_do_projeto_edita_os_dados(self):
        self.como(self.user_ana)  # gerente do T1
        resposta = self.client.patch(self.url(), {'descricao': 'x', 'status': 'em_andamento'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

        for user in [self.user_edu, self.user_bia]:  # executor e membro de fora
            self.como(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(self.url()).status_code, status.HTTP_200_OK)
                resposta = self.client.patch(self.url(), {'descricao': 'y'}, format='json')
                self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_gerente_de_um_projeto_nao_edita_outro(self):
        outro = Projeto.objects.create(nome='T2', empresa=self.empresa, data_inicio=date(2026, 3, 1))
        Alocacao.objects.create(membro=self.ana, projeto=outro, funcao='Executor', escopo='AI')
        self.como(self.user_ana)
        resposta = self.client.patch(f'/api/projetos/{outro.id}/', {'descricao': 'x'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_projeto_concluido_so_admin_altera(self):
        self.concluir_projeto()
        self.como(self.user_ana)
        resposta = self.client.patch(self.url(), {'descricao': 'x'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
        self.como(self.user_admin)
        resposta = self.client.patch(self.url(), {'status': 'em_andamento'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_permissoes_vem_no_projeto(self):
        esperado = {
            'user_ana': {  # gerente
                'editar': True, 'excluir': False, 'gerenciar_equipe': False,
                'ver_documentos': True, 'enviar_documento': True, 'enviar_contrato': True,
            },
            'user_edu': {  # executor
                'editar': False, 'excluir': False, 'gerenciar_equipe': False,
                'ver_documentos': True, 'enviar_documento': True, 'enviar_contrato': False,
            },
            'user_bia': {  # de fora
                'editar': False, 'excluir': False, 'gerenciar_equipe': False,
                'ver_documentos': False, 'enviar_documento': False, 'enviar_contrato': False,
            },
        }
        for nome, permissoes in esperado.items():
            self.como(getattr(self, nome))
            with self.subTest(user=nome):
                self.assertEqual(self.client.get(self.url()).json()['permissoes'], permissoes)


class AlocacaoAcessoTests(AcessoBaseTestCase):
    def nova(self, funcao='Executor'):
        return {'membro': self.bia.id, 'projeto': self.projeto.id, 'funcao': funcao, 'escopo': 'Web'}

    def test_so_o_admin_monta_a_equipe(self):
        for user in [self.user_ana, self.user_edu]:
            self.como(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get('/api/alocacoes/').status_code, status.HTTP_200_OK)
                criar = self.client.post('/api/alocacoes/', self.nova(), format='json')
                self.assertEqual(criar.status_code, status.HTTP_403_FORBIDDEN)
                remover = self.client.delete(f'/api/alocacoes/{self.alocacao.id}/')
                self.assertEqual(remover.status_code, status.HTTP_403_FORBIDDEN)
        self.como(self.user_admin)
        self.assertEqual(
            self.client.post('/api/alocacoes/', self.nova(), format='json').status_code,
            status.HTTP_201_CREATED,
        )

    def test_gerente_nao_muda_a_propria_funcao(self):
        self.como(self.user_ana)  # self.alocacao é a da Ana, gerente do T1
        resposta = self.client.patch(
            f'/api/alocacoes/{self.alocacao.id}/', {'funcao': 'Executor'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_funcao_so_aceita_a_lista(self):
        resposta = self.client.post('/api/alocacoes/', self.nova('gerente'), format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Gerente de projeto', resposta.json()['funcao'][0])

    def test_um_gerente_por_projeto(self):
        resposta = self.client.post('/api/alocacoes/', self.nova('Gerente de projeto'), format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('já tem um gerente: Ana Souza (ANA)', resposta.json()['funcao'][0])

        # Trocar o gerente: a atual vira executora e então a Bia pode ser a gerente.
        self.client.patch(f'/api/alocacoes/{self.alocacao.id}/', {'funcao': 'Executor'}, format='json')
        resposta = self.client.post('/api/alocacoes/', self.nova('Gerente de projeto'), format='json')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED, resposta.json())

        # Editar a própria alocação de gerente (sem trocar a função) continua valendo.
        gerente = Alocacao.objects.get(projeto=self.projeto, funcao='Gerente de projeto')
        resposta = self.client.patch(f'/api/alocacoes/{gerente.id}/', {'escopo': 'AI'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK, resposta.json())

    def test_banco_nao_aceita_dois_gerentes(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Alocacao.objects.create(
                membro=self.bia, projeto=self.projeto, funcao='Gerente de projeto', escopo='Web'
            )

    def test_trocar_de_funcao_muda_as_permissoes_na_hora(self):
        Alocacao.objects.filter(pk=self.alocacao.pk).update(funcao='Executor')
        self.como(self.user_ana)
        resposta = self.client.patch(f'/api/projetos/{self.projeto.id}/', {'descricao': 'x'}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(MEDIA_ROOT=PASTA_MEDIA_TESTES)
class DocumentoAcessoTests(AcessoBaseTestCase):
    def setUp(self):
        super().setUp()
        self.contrato = Documento.objects.create(
            projeto=self.projeto, tipo='contrato', titulo='Contrato',
            arquivo=SimpleUploadedFile('contrato.pdf', b'%PDF contrato'),
        )
        self.ata = Documento.objects.create(
            projeto=self.projeto, tipo='ata', titulo='Ata',
            arquivo=SimpleUploadedFile('ata.pdf', b'%PDF ata'),
        )

    def url(self, documento):
        return f'/api/documentos/{documento.id}/'

    def enviar(self, tipo='ata'):
        dados = {'projeto': self.projeto.id, 'tipo': tipo, 'arquivo': SimpleUploadedFile('a.pdf', b'%PDF')}
        return self.client.post('/api/documentos/', dados, format='multipart')

    def test_membro_fora_do_projeto_nao_ve_documentos(self):
        self.como(self.user_bia)
        self.assertEqual(self.client.get('/api/documentos/').json(), [])
        self.assertEqual(self.client.get(self.url(self.ata)).status_code, status.HTTP_404_NOT_FOUND)
        download = self.client.get(self.url(self.ata) + 'download/')
        self.assertEqual(download.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.enviar().status_code, status.HTTP_403_FORBIDDEN)

    def test_executor_ve_e_envia_mas_nao_exclui_nem_envia_contrato(self):
        self.como(self.user_edu)
        self.assertEqual(len(self.client.get('/api/documentos/').json()), 2)

        download = self.client.get(self.url(self.contrato) + 'download/')
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        self.assertEqual(b''.join(download.streaming_content), b'%PDF contrato')

        self.assertEqual(self.enviar('ata').status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.enviar('contrato').status_code, status.HTTP_403_FORBIDDEN)
        for documento in [self.ata, self.contrato]:
            with self.subTest(documento=documento.titulo):
                self.assertEqual(self.client.delete(self.url(documento)).status_code, status.HTTP_403_FORBIDDEN)

    def test_gerente_ve_envia_e_exclui_inclusive_contrato(self):
        self.como(self.user_ana)
        self.assertEqual(self.enviar('contrato').status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.delete(self.url(self.ata)).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.delete(self.url(self.contrato)).status_code, status.HTTP_204_NO_CONTENT)

    def test_permissao_de_excluir_vem_em_cada_documento(self):
        for user, pode_excluir in [(self.user_ana, True), (self.user_edu, False)]:
            self.como(user)
            documentos = self.client.get(f'/api/documentos/?projeto={self.projeto.id}').json()
            self.assertEqual({d['permissoes']['excluir'] for d in documentos}, {pode_excluir})

    def test_projeto_concluido_fica_so_leitura(self):
        self.concluir_projeto()
        for user in [self.user_ana, self.user_edu]:
            self.como(user)
            with self.subTest(user=user.username):
                self.assertEqual(len(self.client.get('/api/documentos/').json()), 2)
                self.assertEqual(self.enviar().status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(self.client.delete(self.url(self.ata)).status_code, status.HTTP_403_FORBIDDEN)


@HASH_RAPIDO
class CriarAcessosCommandTests(APITestCase):
    def test_cria_logins_sem_escolher_papel(self):
        Membro.objects.create(sigla='AAA', nome='A', email='a@x.com')
        Membro.objects.create(sigla='CCC', nome='C', email='c@x.com', cargo='AG PRJ')
        saida = StringIO()
        call_command('criar_acessos', '--senha', 'Senha-Forte-123', stdout=saida)
        a, c = Membro.objects.order_by('sigla')
        self.assertTrue(a.user.check_password('Senha-Forte-123'))
        self.assertEqual(papel_de(a.user), MEMBRO)
        self.assertEqual(papel_de(c.user), ADMIN)
        self.assertIn('Admin (cargo AG PRJ): CCC', saida.getvalue())
        self.assertIn('2 acesso(s) criado(s)', saida.getvalue())

    def test_avisa_quando_ninguem_tem_o_cargo_ag_prj(self):
        Membro.objects.create(sigla='AAA', nome='A', email='a@x.com')
        saida = StringIO()
        call_command('criar_acessos', '--senha', 'Senha-Forte-123', stdout=saida)
        self.assertIn('ninguém terá o papel de Admin', saida.getvalue())

    def test_exige_senha(self):
        with self.assertRaises(CommandError):
            call_command('criar_acessos', stdout=StringIO())


# ---- prévias dos documentos --------------------------------------------------

def pdf_de_teste():
    import pypdfium2 as pdfium

    documento = pdfium.PdfDocument.new()
    documento.new_page(595, 842)
    saida = BytesIO()
    documento.save(saida)
    return saida.getvalue()


def imagem_de_teste(formato='PNG', tamanho=(1200, 800)):
    from PIL import Image

    saida = BytesIO()
    Image.new('RGB', tamanho, 'orange').save(saida, formato)
    return saida.getvalue()


def zip_de_teste(arquivos):
    import zipfile

    saida = BytesIO()
    with zipfile.ZipFile(saida, 'w') as pacote:
        for nome, conteudo in arquivos.items():
            pacote.writestr(nome, conteudo)
    return saida.getvalue()


DOCX_XML = (
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
    '<w:p><w:r><w:t>Termo de abertura</w:t></w:r></w:p>'
    '<w:p><w:r><w:t xml:space="preserve">Objetivo: </w:t></w:r><w:r><w:t>entregar o MVP.</w:t></w:r></w:p>'
    '</w:body></w:document>'
)


@override_settings(MEDIA_ROOT=PASTA_MEDIA_TESTES)
class PreviaDocumentoTests(AcessoBaseTestCase):
    def documento(self, nome, conteudo):
        return Documento.objects.create(
            projeto=self.projeto, tipo='outro', titulo=nome, arquivo=SimpleUploadedFile(nome, conteudo)
        )

    def previa(self, documento):
        return self.client.get(f'/api/documentos/{documento.id}/previa/')

    def imagem_da_resposta(self, resposta):
        from PIL import Image

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta['Content-Type'], 'image/webp')
        return Image.open(BytesIO(b''.join(resposta.streaming_content)))

    def test_gera_previa_de_cada_formato(self):
        from .previas import LARGURA

        casos = {
            'contrato.pdf': pdf_de_teste(),
            'foto.png': imagem_de_teste(),
            'foto.jpg': imagem_de_teste('JPEG'),
            'notas.txt': 'Reunião de kickoff\n\nPauta: escopo, prazos e riscos. ' * 30,
            'dados.csv': 'nome;valor\nAna;10\nBia;20\n',
            'abertura.docx': zip_de_teste({'word/document.xml': DOCX_XML}),
            'slides.pptx': zip_de_teste({'docProps/thumbnail.jpeg': imagem_de_teste('JPEG', (256, 192))}),
            'planilha.ods': zip_de_teste({'Thumbnails/thumbnail.png': imagem_de_teste('PNG', (256, 256))}),
            'pacote.zip': zip_de_teste({'a.txt': 'x', 'pasta/b.pdf': 'y'}),
        }
        for nome, conteudo in casos.items():
            with self.subTest(arquivo=nome):
                conteudo = conteudo.encode() if isinstance(conteudo, str) else conteudo
                imagem = self.imagem_da_resposta(self.previa(self.documento(nome, conteudo)))
                self.assertLessEqual(imagem.width, LARGURA * 2)
                self.assertGreater(imagem.height, 0)

    def test_texto_do_docx_e_extraido_por_paragrafo(self):
        from .previas import paragrafos_do_docx

        self.assertEqual(paragrafos_do_docx(DOCX_XML), ['Termo de abertura', 'Objetivo: entregar o MVP.'])

    def test_formatos_sem_previa_e_arquivos_corrompidos_dao_404(self):
        sem_previa = self.documento('antigo.doc', b'\xd0\xcf\x11\xe0 binario')
        corrompido = self.documento('quebrado.pdf', b'isto nao e um pdf')
        sem_miniatura = self.documento('planilha.xlsx', zip_de_teste({'xl/workbook.xml': '<x/>'}))
        for documento in [sem_previa, corrompido, sem_miniatura]:
            with self.subTest(arquivo=documento.titulo):
                self.assertEqual(self.previa(documento).status_code, status.HTTP_404_NOT_FOUND)

        dados = self.client.get(f'/api/documentos/?projeto={self.projeto.id}').json()
        tem = {d['titulo']: d['tem_previa'] for d in dados}
        self.assertFalse(tem['antigo.doc'])
        self.assertTrue(tem['quebrado.pdf'])

    def test_previa_fica_em_cache_e_e_apagada_com_o_documento(self):
        from django.core.files.storage import default_storage

        from .previas import caminho_da_previa, obter_previa

        documento = self.documento('foto.png', imagem_de_teste())
        caminho = obter_previa(documento)
        self.assertEqual(caminho, caminho_da_previa(documento))
        modificado = default_storage.get_modified_time(caminho)
        self.assertEqual(obter_previa(documento), caminho)  # não gera de novo
        self.assertEqual(default_storage.get_modified_time(caminho), modificado)

        documento.delete()
        self.assertFalse(default_storage.exists(caminho))

    def test_previa_segue_as_mesmas_permissoes_do_documento(self):
        documento = self.documento('foto.png', imagem_de_teste())
        self.como(self.user_bia)  # não alocada no projeto
        self.assertEqual(self.previa(documento).status_code, status.HTTP_404_NOT_FOUND)
        self.como(self.user_ana)  # alocada
        self.assertEqual(self.previa(documento).status_code, status.HTTP_200_OK)
        self.client.force_authenticate(None)
        self.assertEqual(self.previa(documento).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_fonte_das_previas_tem_acentos(self):
        from PIL import Image, ImageDraw, ImageFont

        from .previas import FONTE

        fonte = ImageFont.truetype(str(FONTE), 17)

        def desenho(caractere):
            imagem = Image.new('L', (40, 40))
            ImageDraw.Draw(imagem).text((8, 8), caractere, font=fonte, fill=255)
            return imagem.tobytes()

        sem_glifo = desenho('￿')  # o "quadrado" de caractere desconhecido
        for letra in 'çãõáéíóúâêôàÁÇ—“”•€':
            with self.subTest(letra=letra):
                self.assertNotEqual(desenho(letra), sem_glifo)
