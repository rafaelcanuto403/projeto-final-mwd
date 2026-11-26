from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/', include('api.urls')),
]
# Os arquivos de /media/ não são servidos publicamente: documentos só saem
# por /api/documentos/<id>/download/, que passa pelo controle de acesso.
