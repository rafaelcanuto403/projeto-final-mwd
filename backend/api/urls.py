from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AlocacaoViewSet,
    DocumentoViewSet,
    EmpresaParceiraViewSet,
    LoginView,
    MeView,
    MembroViewSet,
    ProjetoViewSet,
)

router = DefaultRouter()
router.register(r'empresas', EmpresaParceiraViewSet)
router.register(r'membros', MembroViewSet)
router.register(r'projetos', ProjetoViewSet)
router.register(r'alocacoes', AlocacaoViewSet)
router.register(r'documentos', DocumentoViewSet)

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('', include(router.urls)),
]
