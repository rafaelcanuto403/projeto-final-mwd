from pathlib import Path

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import (
    MAX_MEMBROS_POR_PROJETO, Alocacao, Documento, EmpresaParceira, Membro, Projeto,
    eh_cargo_unico, normalizar_cargo,
)
from .previas import tem_previa
from .permissoes import CARGO_ADMIN, CRIAR, EDITAR, EXCLUIR, LER, eh_cargo_admin, papel_de, pode

User = get_user_model()


def usuario_da_requisicao(serializer):
    request = serializer.context.get('request')
    return getattr(request, 'user', None)


def sincronizar_usuario(membro, senha=None):
    """Cria/atualiza o User de login do membro (username = e-mail).

    Não há papel gravado: Admin vem do cargo AG PRJ e todo outro membro é Membro.
    Sem senha, o membro fica cadastrado mas sem conseguir entrar.
    """
    user = membro.user
    if user is None:
        user = User(username=membro.email)
        user.set_unusable_password()
    user.username = membro.email
    user.email = membro.email
    user.first_name = membro.nome[:150]
    if senha:
        user.set_password(senha)
    user.save()

    if membro.user_id != user.pk:
        membro.user = user
        membro.save(update_fields=['user'])
    user.__dict__.pop('_papel', None)
    return user


def passar_cargo(novo_cargo, membro_pk=None):
    """Cada cargo (exceto os repetíveis) tem um único ocupante: dar o cargo a alguém tira o
    cargo de quem o tinha. Vale também para o AG PRJ, e com ele passa o papel de Admin."""
    if not eh_cargo_unico(novo_cargo):
        return None
    anterior = Membro.objects.filter(cargo__iexact=normalizar_cargo(novo_cargo)).exclude(pk=membro_pk).first()
    if anterior is not None:
        anterior.cargo = ''
        anterior.save(update_fields=['cargo'])
    return anterior


def unico(model, campo, mensagem):
    validadores_do_model = list(model._meta.get_field(campo).validators)
    return validadores_do_model + [UniqueValidator(queryset=model.objects.all(), message=mensagem)]


class EmpresaParceiraSerializer(serializers.ModelSerializer):
    total_projetos = serializers.SerializerMethodField()

    class Meta:
        model = EmpresaParceira
        fields = ['id', 'nome', 'logo_url', 'total_projetos']
        extra_kwargs = {
            'nome': {'validators': unico(EmpresaParceira, 'nome', 'Já existe uma empresa com este nome.')},
        }

    def get_total_projetos(self, obj):
        total = getattr(obj, 'total_projetos', None)
        return total if total is not None else obj.projetos.count()


class MembroSerializer(serializers.ModelSerializer):
    total_projetos = serializers.SerializerMethodField()
    papel = serializers.SerializerMethodField()  # derivado do cargo: não se escolhe
    senha = serializers.CharField(
        write_only=True,
        required=False,
        trim_whitespace=False,
        style={'input_type': 'password'},
    )
    tem_acesso = serializers.SerializerMethodField()
    permissoes = serializers.SerializerMethodField()

    class Meta:
        model = Membro
        fields = [
            'id', 'sigla', 'nome', 'email', 'foto_url', 'cargo', 'total_projetos',
            'papel', 'senha', 'tem_acesso', 'permissoes',
        ]
        extra_kwargs = {
            'sigla': {'validators': unico(Membro, 'sigla', 'Já existe um membro com esta sigla.')},
            'email': {'validators': unico(Membro, 'email', 'Já existe um membro com este e-mail.')},
            # A constraint de cargo único é tratada como passagem de cargo (passar_cargo),
            # não como erro de validação.
            'cargo': {'validators': []},
        }

    def get_total_projetos(self, obj):
        total = getattr(obj, 'total_projetos', None)
        return total if total is not None else obj.alocacoes.values('projeto').distinct().count()

    def get_papel(self, obj):
        return papel_de(obj.user) if obj.user_id else None

    def get_tem_acesso(self, obj):
        return bool(obj.user_id and obj.user.is_active and obj.user.has_usable_password())

    def get_permissoes(self, obj):
        user = usuario_da_requisicao(self)
        return {
            'editar': pode(user, EDITAR, 'membro', obj),
            'excluir': pode(user, EXCLUIR, 'membro', obj),
        }

    def validate_email(self, email):
        conflito = User.objects.filter(username=email)
        if self.instance is not None and self.instance.user_id:
            conflito = conflito.exclude(pk=self.instance.user_id)
        if conflito.exists():
            raise serializers.ValidationError('Já existe um usuário com este e-mail.')
        return email

    def validate_senha(self, senha):
        try:
            password_validation.validate_password(senha)
        except DjangoValidationError as erro:
            raise serializers.ValidationError(list(erro.messages))
        return senha

    def validate_cargo(self, cargo):
        user = usuario_da_requisicao(self)
        alvo = getattr(self.instance, 'user', None)
        eh_o_proprio = alvo is not None and user is not None and alvo.pk == user.pk
        if eh_o_proprio and eh_cargo_admin(self.instance.cargo) and not eh_cargo_admin(cargo):
            raise serializers.ValidationError(
                f'Você não pode simplesmente deixar o cargo {CARGO_ADMIN}: o sistema ficaria sem Admin. '
                f'Para passá-lo, defina {CARGO_ADMIN} no cadastro do seu sucessor.'
            )
        return cargo

    @transaction.atomic
    def create(self, validated_data):
        senha = validated_data.pop('senha', None)
        passar_cargo(validated_data.get('cargo'))
        membro = super().create(validated_data)
        sincronizar_usuario(membro, senha)
        return membro

    @transaction.atomic
    def update(self, instance, validated_data):
        senha = validated_data.pop('senha', None)
        if 'cargo' in validated_data:
            passar_cargo(validated_data['cargo'], instance.pk)
        membro = super().update(instance, validated_data)
        sincronizar_usuario(membro, senha)
        return membro

    def to_internal_value(self, data):
        data = data.copy()
        if isinstance(data.get('sigla'), str):
            data['sigla'] = data['sigla'].strip().upper()
        if isinstance(data.get('email'), str):
            data['email'] = data['email'].strip().lower()
        return super().to_internal_value(data)


class ProjetoSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.CharField(source='empresa.nome', read_only=True)
    empresa_logo_url = serializers.CharField(source='empresa.logo_url', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    permissoes = serializers.SerializerMethodField()

    class Meta:
        model = Projeto
        fields = [
            'id', 'nome', 'descricao', 'empresa', 'empresa_nome', 'empresa_logo_url',
            'status', 'status_display', 'data_inicio', 'data_fim_prevista', 'permissoes',
        ]

    def get_permissoes(self, obj):
        user = usuario_da_requisicao(self)
        documento = Documento(projeto=obj, tipo=Documento.Tipo.OUTRO)
        contrato = Documento(projeto=obj, tipo=Documento.Tipo.CONTRATO)
        return {
            'editar': pode(user, EDITAR, 'projeto', obj),
            'excluir': pode(user, EXCLUIR, 'projeto', obj),
            'gerenciar_equipe': pode(user, CRIAR, 'alocacao', Alocacao(projeto=obj)),
            'ver_documentos': pode(user, LER, 'documento', documento),
            'enviar_documento': pode(user, CRIAR, 'documento', documento),
            'enviar_contrato': pode(user, CRIAR, 'documento', contrato),
        }

    def validate(self, data):
        inicio = data.get('data_inicio', getattr(self.instance, 'data_inicio', None))
        fim = data.get('data_fim_prevista', getattr(self.instance, 'data_fim_prevista', None))
        if inicio and fim and fim < inicio:
            raise serializers.ValidationError(
                {'data_fim_prevista': 'A data de fim prevista não pode ser anterior à data de início.'}
            )
        return data


class AlocacaoSerializer(serializers.ModelSerializer):
    membro_nome = serializers.CharField(source='membro.nome', read_only=True)
    membro_sigla = serializers.CharField(source='membro.sigla', read_only=True)
    membro_foto_url = serializers.CharField(source='membro.foto_url', read_only=True)
    projeto_nome = serializers.CharField(source='projeto.nome', read_only=True)
    projeto_status = serializers.CharField(source='projeto.status', read_only=True)
    projeto_status_display = serializers.CharField(source='projeto.get_status_display', read_only=True)
    projeto_data_inicio = serializers.DateField(source='projeto.data_inicio', read_only=True)
    empresa_nome = serializers.CharField(source='projeto.empresa.nome', read_only=True)
    empresa_logo_url = serializers.CharField(source='projeto.empresa.logo_url', read_only=True)

    class Meta:
        model = Alocacao
        fields = [
            'id', 'membro', 'membro_nome', 'membro_sigla', 'membro_foto_url',
            'projeto', 'projeto_nome', 'projeto_status', 'projeto_status_display',
            'projeto_data_inicio', 'empresa_nome', 'empresa_logo_url', 'funcao', 'escopo',
        ]
        extra_kwargs = {
            'escopo': {
                'error_messages': {
                    'invalid_choice': 'Escolha um escopo da lista: '
                    + ', '.join(Alocacao.Escopo.values) + '.',
                },
            },
            'funcao': {
                'error_messages': {
                    'invalid_choice': 'Escolha uma função da lista: '
                    + ', '.join(Alocacao.Funcao.values) + '.',
                },
            },
        }
        # "Um gerente por projeto" é validado em validate(), com uma mensagem que diz quem é o
        # gerente (o validador automático do DRF para a constraint daria um erro genérico).
        validators = []

    def validate(self, attrs):
        projeto = attrs.get('projeto') or (self.instance and self.instance.projeto)
        funcao = attrs.get('funcao', getattr(self.instance, 'funcao', None))
        if projeto is not None and funcao == Alocacao.Funcao.GERENTE_DE_PROJETO:
            gerente = projeto.alocacoes.filter(funcao=funcao).select_related('membro')
            if self.instance is not None:
                gerente = gerente.exclude(pk=self.instance.pk)
            gerente = gerente.first()
            if gerente is not None:
                raise serializers.ValidationError({
                    'funcao': f'O projeto {projeto.nome} já tem um gerente: {gerente.membro.nome} '
                    f'({gerente.membro.sigla}). Mude a função dele para Executor antes.'
                })
        if projeto is not None:
            outros = projeto.alocacoes.all()
            if self.instance is not None:
                outros = outros.exclude(pk=self.instance.pk)
            if outros.count() >= MAX_MEMBROS_POR_PROJETO:
                raise serializers.ValidationError(
                    f'O projeto {projeto.nome} já tem {MAX_MEMBROS_POR_PROJETO} membros, '
                    'o máximo permitido. Remova alguém da equipe antes de adicionar outro.'
                )
        return attrs


EXTENSOES_DOCUMENTO = {
    '.pdf', '.doc', '.docx', '.odt', '.txt',
    '.xls', '.xlsx', '.ods', '.csv',
    '.ppt', '.pptx', '.odp',
    '.png', '.jpg', '.jpeg', '.zip',
}
TAMANHO_MAXIMO_DOCUMENTO = 20 * 1024 * 1024


class DocumentoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    arquivo = serializers.FileField(write_only=True)
    nome_arquivo = serializers.SerializerMethodField()
    tamanho = serializers.SerializerMethodField()
    tem_previa = serializers.SerializerMethodField()
    permissoes = serializers.SerializerMethodField()

    class Meta:
        model = Documento
        fields = [
            'id', 'projeto', 'tipo', 'tipo_display', 'titulo',
            'arquivo', 'nome_arquivo', 'tamanho', 'enviado_em', 'tem_previa', 'permissoes',
        ]
        extra_kwargs = {'titulo': {'required': False, 'allow_blank': True}}

    def get_permissoes(self, obj):
        return {'excluir': pode(usuario_da_requisicao(self), EXCLUIR, 'documento', obj)}

    def get_tem_previa(self, obj):
        return bool(obj.arquivo) and tem_previa(obj)

    def get_nome_arquivo(self, obj):
        return Path(obj.arquivo.name).name if obj.arquivo else None

    def get_tamanho(self, obj):
        try:
            return obj.arquivo.size
        except (FileNotFoundError, ValueError):
            return None

    def validate_arquivo(self, arquivo):
        extensao = Path(arquivo.name).suffix.lower()
        if extensao not in EXTENSOES_DOCUMENTO:
            raise serializers.ValidationError(
                'Formato não aceito. Use PDF, Word, Excel, PowerPoint, '
                'OpenDocument, TXT, CSV, imagem (PNG/JPG) ou ZIP.'
            )
        if arquivo.size > TAMANHO_MAXIMO_DOCUMENTO:
            raise serializers.ValidationError('O arquivo deve ter no máximo 20 MB.')
        return arquivo

    def validate(self, attrs):
        titulo = (attrs.get('titulo') or '').strip()
        if not titulo and 'arquivo' in attrs:
            titulo = Path(attrs['arquivo'].name).stem
        if 'titulo' in attrs or 'arquivo' in attrs:
            if not titulo:
                raise serializers.ValidationError({'titulo': 'Informe um título.'})
            attrs['titulo'] = titulo[:150]
        return attrs
