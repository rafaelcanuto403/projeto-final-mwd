from pathlib import Path

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import MAX_MEMBROS_POR_PROJETO, Alocacao, Documento, EmpresaParceira, Membro, Projeto


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

    class Meta:
        model = Membro
        fields = ['id', 'sigla', 'nome', 'email', 'foto_url', 'cargo', 'total_projetos']
        extra_kwargs = {
            'sigla': {'validators': unico(Membro, 'sigla', 'Já existe um membro com esta sigla.')},
            'email': {'validators': unico(Membro, 'email', 'Já existe um membro com este e-mail.')},
        }

    def get_total_projetos(self, obj):
        total = getattr(obj, 'total_projetos', None)
        return total if total is not None else obj.alocacoes.values('projeto').distinct().count()

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

    class Meta:
        model = Projeto
        fields = [
            'id', 'nome', 'descricao', 'empresa', 'empresa_nome', 'empresa_logo_url',
            'status', 'status_display', 'data_inicio', 'data_fim_prevista',
        ]

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
        }

    def validate(self, attrs):
        projeto = attrs.get('projeto') or (self.instance and self.instance.projeto)
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
    arquivo_url = serializers.SerializerMethodField()
    nome_arquivo = serializers.SerializerMethodField()
    tamanho = serializers.SerializerMethodField()

    class Meta:
        model = Documento
        fields = [
            'id', 'projeto', 'tipo', 'tipo_display', 'titulo',
            'arquivo', 'arquivo_url', 'nome_arquivo', 'tamanho', 'enviado_em',
        ]
        extra_kwargs = {'titulo': {'required': False, 'allow_blank': True}}

    def get_arquivo_url(self, obj):
        return obj.arquivo.url if obj.arquivo else None

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
