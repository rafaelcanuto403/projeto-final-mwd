"""Controle de acesso misto: RBAC (papel do usuário) + ABAC (atributos do objeto).

Toda decisão passa por `pode(user, acao, recurso, obj)`. Quando `obj` é None a
pergunta é "este papel pode, em algum caso, fazer isso?" (usada para liberar a
rota e montar o menu); com `obj` as regras de atributo também são avaliadas.

Papéis (RBAC) — derivados, nada é atribuído à mão:
  Admin   quem tem o cargo AG PRJ (um único membro, ver models.CARGO_ADMIN);
  Membro  qualquer outro membro do NEO com login ativo.

Função no projeto (ABAC) — vem da alocação do membro naquele projeto:
  Gerente de projeto (um por projeto) e Executor.

Matriz (ver README):
                Admin   Gerente do projeto      Executor (alocado)       Membro fora do projeto
  empresa       CRUD    ler                     ler                      ler
  membro        CRUD    ler + próprio perfil    ler + próprio perfil     ler + próprio perfil
  projeto       CRUD    ler + editar*           ler                      ler
  alocacao      CRUD    ler                     ler                      ler
  documento     CRUD    ver/enviar/excluir*     ver; enviar* (menos      —
                                                contrato)

  * projeto concluído fica somente leitura para quem não é Admin.
"""

from rest_framework.permissions import BasePermission

from .models import CARGO_ADMIN, Alocacao, Documento, Projeto, eh_cargo_admin  # noqa: F401 (reexporta)

ADMIN = 'admin'
MEMBRO = 'membro'
PAPEIS = [ADMIN, MEMBRO]

GERENTE_DE_PROJETO = Alocacao.Funcao.GERENTE_DE_PROJETO
EXECUTOR = Alocacao.Funcao.EXECUTOR

LER, CRIAR, EDITAR, EXCLUIR = 'ler', 'criar', 'editar', 'excluir'

CAMPOS_DO_PROPRIO_PERFIL = {'nome', 'foto_url', 'senha'}


def membro_de(user):
    if user is None or not user.is_authenticated:
        return None
    return getattr(user, 'membro', None)


def papel_de(user):
    """Admin para o AG PRJ, Membro para os demais; None (sem acesso) para quem não é membro."""
    if user is None or not user.is_authenticated or not user.is_active:
        return None
    if not hasattr(user, '_papel'):
        membro = membro_de(user)
        if membro is None:
            user._papel = None  # sem cadastro de membro do NEO não há acesso
        else:
            user._papel = ADMIN if eh_cargo_admin(membro.cargo) else MEMBRO
    return user._papel


def funcoes_nos_projetos(user):
    """{id do projeto: função} do usuário (calculado uma vez por requisição)."""
    if not hasattr(user, '_funcoes'):
        membro = membro_de(user)
        user._funcoes = dict(membro.alocacoes.values_list('projeto_id', 'funcao')) if membro else {}
    return user._funcoes


def projetos_alocados(user):
    return set(funcoes_nos_projetos(user))


def esta_alocado(user, projeto):
    return projeto is not None and projeto.pk in funcoes_nos_projetos(user)


def eh_gerente_do_projeto(user, projeto):
    return projeto is not None and funcoes_nos_projetos(user).get(projeto.pk) == GERENTE_DE_PROJETO


def concluido(projeto):
    return projeto is not None and projeto.status == Projeto.Status.CONCLUIDO


# ---- regras por recurso ----------------------------------------------------
# Daqui para baixo, papel == MEMBRO sempre que não for ADMIN.

def _empresa(user, papel, acao, obj):
    return acao == LER or papel == ADMIN


def _membro(user, papel, acao, obj):
    if acao == LER or papel == ADMIN:
        return True
    if acao == EDITAR:
        # Qualquer um edita o próprio perfil (campos limitados na view).
        return obj is None or obj.pk == getattr(membro_de(user), 'pk', None)
    return False


def _projeto(user, papel, acao, obj):
    if acao == LER or papel == ADMIN:
        return True
    if acao == EDITAR:
        # Só o gerente daquele projeto edita os dados, enquanto não estiver concluído.
        return obj is None or (eh_gerente_do_projeto(user, obj) and not concluido(obj))
    return False  # criar e excluir projetos: só o Admin


def _alocacao(user, papel, acao, obj):
    return acao == LER or papel == ADMIN  # a equipe é montada pelo Admin


def _documento(user, papel, acao, obj):
    if papel == ADMIN:
        return True
    if obj is None:
        return True  # depende do projeto e da função: decidido com o documento em mãos
    projeto = obj.projeto
    if not esta_alocado(user, projeto):
        return False
    if acao == LER:
        return True
    if concluido(projeto):
        return False
    if eh_gerente_do_projeto(user, projeto):
        return True  # o gerente envia e exclui qualquer documento, inclusive contrato
    return acao == CRIAR and obj.tipo != Documento.Tipo.CONTRATO  # executor: só envia


REGRAS = {
    'empresa': _empresa,
    'membro': _membro,
    'projeto': _projeto,
    'alocacao': _alocacao,
    'documento': _documento,
}


def pode(user, acao, recurso, obj=None):
    papel = papel_de(user)
    if papel is None:
        return False
    return REGRAS[recurso](user, papel, acao, obj)


# ---- integração com o DRF --------------------------------------------------

ACOES_DA_VIEW = {
    'list': LER,
    'retrieve': LER,
    'download': LER,
    'previa': LER,
    'create': CRIAR,
    'update': EDITAR,
    'partial_update': EDITAR,
    'destroy': EXCLUIR,
}


class PoliticaDeAcesso(BasePermission):
    """Usa `view.recurso` e a action do ViewSet para consultar `pode()`."""

    message = 'Você não tem permissão para realizar esta ação.'

    def _acao(self, view):
        return ACOES_DA_VIEW.get(view.action, LER)

    def has_permission(self, request, view):
        if papel_de(request.user) is None:
            return False
        return pode(request.user, self._acao(view), view.recurso)

    def has_object_permission(self, request, view, obj):
        return pode(request.user, self._acao(view), view.recurso, obj)


class TemPapel(BasePermission):
    """Apenas usuários autenticados que são membros do NEO."""

    def has_permission(self, request, view):
        return papel_de(request.user) is not None
