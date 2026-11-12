from django.db.models import Count, ProtectedError
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Alocacao, EmpresaParceira, Membro, Projeto
from .serializers import (
    AlocacaoSerializer,
    EmpresaParceiraSerializer,
    MembroSerializer,
    ProjetoSerializer,
)


class EmpresaParceiraViewSet(viewsets.ModelViewSet):
    # Empresas com mais projetos aparecem primeiro, como nos cards do frontend
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


class MembroViewSet(viewsets.ModelViewSet):
    queryset = Membro.objects.all().order_by('nome')
    serializer_class = MembroSerializer


class ProjetoViewSet(viewsets.ModelViewSet):
    queryset = Projeto.objects.select_related('empresa').order_by('-data_inicio')
    serializer_class = ProjetoSerializer

    def get_queryset(self):
        # Filtro opcional: /api/projetos/?empresa=<id>
        queryset = super().get_queryset()
        empresa_id = self.request.query_params.get('empresa')
        if empresa_id is not None:
            if not empresa_id.isdigit():
                raise ValidationError({'empresa': 'Informe o id numérico da empresa.'})
            queryset = queryset.filter(empresa_id=empresa_id)
        return queryset


class AlocacaoViewSet(viewsets.ModelViewSet):
    queryset = Alocacao.objects.select_related('membro', 'projeto').order_by('id')
    serializer_class = AlocacaoSerializer

    def get_queryset(self):
        # Filtros opcionais: /api/alocacoes/?projeto=<id> e/ou ?membro=<id>
        queryset = super().get_queryset()
        for campo in ('projeto', 'membro'):
            valor = self.request.query_params.get(campo)
            if valor is not None:
                if not valor.isdigit():
                    raise ValidationError({campo: f'Informe o id numérico do {campo}.'})
                queryset = queryset.filter(**{f'{campo}_id': valor})
        return queryset
