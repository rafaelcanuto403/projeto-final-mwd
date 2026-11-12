from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Alocacao, EmpresaParceira, Membro, Projeto


def unico(model, campo, mensagem):
    """Validadores do campo do model + checagem de unicidade com mensagem em português."""
    validadores_do_model = list(model._meta.get_field(campo).validators)
    return validadores_do_model + [UniqueValidator(queryset=model.objects.all(), message=mensagem)]


class EmpresaParceiraSerializer(serializers.ModelSerializer):
    # Quantidade de projetos da empresa (exibida nos cards "N projetos")
    total_projetos = serializers.SerializerMethodField()

    class Meta:
        model = EmpresaParceira
        fields = ['id', 'nome', 'logo_url', 'total_projetos']
        extra_kwargs = {
            'nome': {'validators': unico(EmpresaParceira, 'nome', 'Já existe uma empresa com este nome.')},
        }

    def get_total_projetos(self, obj):
        # Na listagem vem pronto do annotate da view; em create/update, conta direto
        total = getattr(obj, 'total_projetos', None)
        return total if total is not None else obj.projetos.count()


class MembroSerializer(serializers.ModelSerializer):
    # Em quantos projetos o membro está alocado (exibido na lista de membros)
    total_projetos = serializers.SerializerMethodField()

    class Meta:
        model = Membro
        fields = ['id', 'sigla', 'nome', 'email', 'foto_url', 'total_projetos']
        extra_kwargs = {
            'sigla': {'validators': unico(Membro, 'sigla', 'Já existe um membro com esta sigla.')},
            'email': {'validators': unico(Membro, 'email', 'Já existe um membro com este e-mail.')},
        }

    def get_total_projetos(self, obj):
        # Na listagem vem pronto do annotate da view; em create/update, conta direto
        total = getattr(obj, 'total_projetos', None)
        return total if total is not None else obj.alocacoes.values('projeto').distinct().count()

    def to_internal_value(self, data):
        # Normaliza antes da validação: aceita " abc " e salva "ABC"
        # (o validador do model exige 3 letras maiúsculas e roda antes dos validate_*)
        data = data.copy()
        if isinstance(data.get('sigla'), str):
            data['sigla'] = data['sigla'].strip().upper()
        if isinstance(data.get('email'), str):
            data['email'] = data['email'].strip().lower()
        return super().to_internal_value(data)


class ProjetoSerializer(serializers.ModelSerializer):
    # Campos só de leitura para facilitar a exibição no frontend
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
    # Dados do projeto e da EP para o perfil do membro
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
