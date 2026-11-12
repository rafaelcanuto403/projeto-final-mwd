from django.contrib import admin

from .models import Alocacao, EmpresaParceira, Membro, Projeto


@admin.register(EmpresaParceira)
class EmpresaParceiraAdmin(admin.ModelAdmin):
    list_display = ('nome', 'logo_url')
    search_fields = ('nome',)


@admin.register(Membro)
class MembroAdmin(admin.ModelAdmin):
    list_display = ('sigla', 'nome', 'email')
    search_fields = ('sigla', 'nome', 'email')


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'status', 'data_inicio', 'data_fim_prevista')
    list_filter = ('status', 'empresa')
    search_fields = ('nome',)


@admin.register(Alocacao)
class AlocacaoAdmin(admin.ModelAdmin):
    list_display = ('membro', 'projeto', 'funcao', 'escopo')
    list_filter = ('projeto',)
