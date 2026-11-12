from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AlocacaoViewSet, EmpresaParceiraViewSet, MembroViewSet, ProjetoViewSet

router = DefaultRouter()
router.register(r'empresas', EmpresaParceiraViewSet)
router.register(r'membros', MembroViewSet)
router.register(r'projetos', ProjetoViewSet)
router.register(r'alocacoes', AlocacaoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
