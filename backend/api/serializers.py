from rest_framework import serializers

from .models import Alocacao, EmpresaParceira, Membro, Projeto


class EmpresaParceiraSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmpresaParceira
        fields = ['id', 'nome', 'logo_url']


class MembroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membro
        fields = ['id', 'sigla', 'nome', 'email', 'foto_url']


class ProjetoSerializer(serializers.ModelSerializer):
    # Campos só de leitura para facilitar a exibição no frontend
    empresa_nome = serializers.CharField(source='empresa.nome', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Projeto
        fields = [
            'id', 'nome', 'descricao', 'empresa', 'empresa_nome',
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
    projeto_nome = serializers.CharField(source='projeto.nome', read_only=True)

    class Meta:
        model = Alocacao
        fields = ['id', 'membro', 'membro_nome', 'projeto', 'projeto_nome', 'funcao', 'escopo']
