from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Alocacao, EmpresaParceira, Membro, Projeto
from .serializers import (
    AlocacaoSerializer,
    EmpresaParceiraSerializer,
    MembroSerializer,
    ProjetoSerializer,
)


class EmpresaParceiraViewSet(viewsets.ModelViewSet):
    queryset = EmpresaParceira.objects.all().order_by('nome')
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


class AlocacaoViewSet(viewsets.ModelViewSet):
    queryset = Alocacao.objects.select_related('membro', 'projeto').order_by('id')
    serializer_class = AlocacaoSerializer
