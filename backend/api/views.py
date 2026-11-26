from pathlib import Path

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Count, ProtectedError
from django.core.files.storage import default_storage
from django.http import FileResponse
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Alocacao, Documento, EmpresaParceira, Membro, Projeto
from .previas import obter_previa
from .permissoes import (
    ADMIN,
    CAMPOS_DO_PROPRIO_PERFIL,
    CRIAR,
    EDITAR,
    EXCLUIR,
    PoliticaDeAcesso,
    TemPapel,
    membro_de,
    papel_de,
    pode,
    projetos_alocados,
)
from .serializers import (
    AlocacaoSerializer,
    DocumentoSerializer,
    EmpresaParceiraSerializer,
    MembroSerializer,
    ProjetoSerializer,
)

User = get_user_model()


class ControleDeAcessoMixin:
    """Liga o ViewSet à política de acesso. Cada ViewSet informa o seu `recurso`."""

    permission_classes = [PoliticaDeAcesso]
    recurso = None

    def exigir(self, acao, obj):
        if not pode(self.request.user, acao, self.recurso, obj):
            raise PermissionDenied(PoliticaDeAcesso.message)


def filtro_numerico(request, campo):
    valor = request.query_params.get(campo)
    if valor is not None and not valor.isdigit():
        raise ValidationError({campo: f'Informe o id numérico do {campo}.'})
    return valor


class EmpresaParceiraViewSet(ControleDeAcessoMixin, viewsets.ModelViewSet):
    recurso = 'empresa'
    queryset = EmpresaParceira.objects.annotate(
        total_projetos=Count('projetos')
    ).order_by('-total_projetos', 'nome')
    serializer_class = EmpresaParceiraSerializer

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'Não é possível excluir uma empresa que possui projetos vinculados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MembroViewSet(ControleDeAcessoMixin, viewsets.ModelViewSet):
    recurso = 'membro'
    queryset = (
        Membro.objects.annotate(total_projetos=Count('alocacoes__projeto', distinct=True))
        .select_related('user')
        .prefetch_related('user__groups')
        .order_by('nome')
    )
    serializer_class = MembroSerializer

    def perform_update(self, serializer):
        if papel_de(self.request.user) != ADMIN:
            # ABAC: no próprio perfil só alguns campos podem mudar.
            membro = serializer.instance
            alterados = {
                campo
                for campo, valor in serializer.validated_data.items()
                if campo == 'senha' or getattr(membro, campo, None) != valor
            }
            proibidos = alterados - CAMPOS_DO_PROPRIO_PERFIL
            if proibidos:
                raise PermissionDenied(
                    'No seu perfil você só pode alterar nome, foto e senha. '
                    f'Campos não permitidos: {", ".join(sorted(proibidos))}.'
                )
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id and instance.user_id == self.request.user.pk:
            raise ValidationError({'detail': 'Você não pode excluir o seu próprio cadastro.'})
        instance.delete()


class ProjetoViewSet(ControleDeAcessoMixin, viewsets.ModelViewSet):
    recurso = 'projeto'
    queryset = Projeto.objects.select_related('empresa').order_by('-data_inicio')
    serializer_class = ProjetoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        empresa_id = filtro_numerico(self.request, 'empresa')
        if empresa_id is not None:
            queryset = queryset.filter(empresa_id=empresa_id)
        return queryset

    def perform_create(self, serializer):
        self.exigir(CRIAR, Projeto(**serializer.validated_data))
        serializer.save()


class AlocacaoViewSet(ControleDeAcessoMixin, viewsets.ModelViewSet):
    recurso = 'alocacao'
    queryset = Alocacao.objects.select_related('membro', 'projeto__empresa').order_by('id')
    serializer_class = AlocacaoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        for campo in ('projeto', 'membro'):
            valor = filtro_numerico(self.request, campo)
            if valor is not None:
                queryset = queryset.filter(**{f'{campo}_id': valor})
        return queryset

    def perform_create(self, serializer):
        self.exigir(CRIAR, Alocacao(projeto=serializer.validated_data['projeto']))
        serializer.save()

    def perform_update(self, serializer):
        if 'projeto' in serializer.validated_data:
            self.exigir(EDITAR, Alocacao(projeto=serializer.validated_data['projeto']))
        serializer.save()


class DocumentoViewSet(ControleDeAcessoMixin, viewsets.ModelViewSet):
    recurso = 'documento'
    queryset = Documento.objects.select_related('projeto').order_by('-enviado_em')
    serializer_class = DocumentoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # ABAC na listagem: membro só enxerga documentos dos projetos em que está alocado.
        if papel_de(self.request.user) != ADMIN:
            queryset = queryset.filter(projeto_id__in=projetos_alocados(self.request.user))
        projeto_id = filtro_numerico(self.request, 'projeto')
        if projeto_id is not None:
            queryset = queryset.filter(projeto_id=projeto_id)
        return queryset

    def perform_create(self, serializer):
        dados = serializer.validated_data
        self.exigir(CRIAR, Documento(projeto=dados['projeto'], tipo=dados.get('tipo', Documento.Tipo.OUTRO)))
        serializer.save()

    def perform_update(self, serializer):
        atual, dados = serializer.instance, serializer.validated_data
        self.exigir(
            EDITAR,
            Documento(projeto=dados.get('projeto', atual.projeto), tipo=dados.get('tipo', atual.tipo)),
        )
        serializer.save()

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        documento = self.get_object()
        try:
            arquivo = documento.arquivo.open('rb')
        except (FileNotFoundError, ValueError):
            raise NotFound('O arquivo deste documento não foi encontrado.')
        return FileResponse(arquivo, as_attachment=True, filename=Path(documento.arquivo.name).name)

    @action(detail=True, methods=['get'])
    def previa(self, request, pk=None):
        """Miniatura da primeira página (WebP), gerada na primeira vez e depois servida do cache."""
        caminho = obter_previa(self.get_object())
        if caminho is None:
            raise NotFound('Este documento não tem prévia.')
        resposta = FileResponse(default_storage.open(caminho, 'rb'), content_type='image/webp')
        resposta['Cache-Control'] = 'private, max-age=86400'
        return resposta


# ---- autenticação ------------------------------------------------------------

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    senha = serializers.CharField(trim_whitespace=False)


class LoginView(APIView):
    """Troca e-mail + senha por um par de tokens JWT (access + refresh)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'login'

    def get_authenticate_header(self, request):
        return 'Bearer realm="api"'  # faz o DRF responder 401 (e não 403) a credenciais inválidas

    def post(self, request):
        entrada = LoginSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        email = entrada.validated_data['email'].strip().lower()

        conta = User.objects.filter(email__iexact=email).first()
        user = conta and authenticate(
            request, username=conta.username, password=entrada.validated_data['senha']
        )
        if not user or papel_de(user) is None:
            raise AuthenticationFailed('E-mail ou senha incorretos.')

        refresh = RefreshToken.for_user(user)
        return Response({'access': str(refresh.access_token), 'refresh': str(refresh)})


class MeView(APIView):
    """Quem está logado, qual o papel e o que pode fazer (para o frontend montar a tela)."""

    permission_classes = [TemPapel]

    def get(self, request):
        user = request.user
        membro = membro_de(user)

        def acoes(recurso, *lista):
            return {acao: pode(user, acao, recurso) for acao in lista}

        return Response({
            'id': user.pk,
            'email': user.email,
            'nome': membro.nome if membro else (user.get_full_name() or user.username),
            'papel': papel_de(user),
            'membro': membro and {
                'id': membro.pk,
                'sigla': membro.sigla,
                'nome': membro.nome,
                'foto_url': membro.foto_url,
            },
            'permissoes': {
                'empresa': acoes('empresa', CRIAR, EDITAR, EXCLUIR),
                'membro': acoes('membro', CRIAR, EXCLUIR),
                'projeto': acoes('projeto', CRIAR),
            },
        })
