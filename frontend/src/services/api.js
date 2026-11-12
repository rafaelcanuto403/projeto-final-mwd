// URL base da API Django. Em desenvolvimento, o Vite repassa /api para 127.0.0.1:8000
// (ver vite.config.js). Pode ser trocada com a variável VITE_API_URL num arquivo .env
const API_URL = import.meta.env.VITE_API_URL ?? '/api'

// Erro da API com os erros de cada campo (ex.: { nome: ['Este campo é obrigatório.'] })
export class ApiError extends Error {
  constructor(mensagem, campos = {}) {
    super(mensagem)
    this.campos = campos
  }
}

async function request(caminho, { metodo = 'GET', corpo } = {}) {
  const resposta = await fetch(`${API_URL}${caminho}`, {
    method: metodo,
    headers: { 'Content-Type': 'application/json' },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  })

  if (!resposta.ok) {
    const dados = await resposta.json().catch(() => null)
    if (dados?.detail) throw new ApiError(dados.detail)
    if (dados && typeof dados === 'object') {
      throw new ApiError('Verifique os campos destacados.', dados)
    }
    throw new ApiError(`Erro ${resposta.status} ao acessar a API.`)
  }

  return resposta.status === 204 ? null : resposta.json()
}

const enviar = (metodo) => (caminho, corpo) => request(caminho, { metodo, corpo })
const post = enviar('POST')
const patch = enviar('PATCH')
const remover = (caminho) => request(caminho, { metodo: 'DELETE' })

export const api = {
  // Empresas parceiras
  listarEmpresas: () => request('/empresas/'),
  buscarEmpresa: (id) => request(`/empresas/${id}/`),
  criarEmpresa: (dados) => post('/empresas/', dados),
  atualizarEmpresa: (id, dados) => patch(`/empresas/${id}/`, dados),
  excluirEmpresa: (id) => remover(`/empresas/${id}/`),

  // Projetos
  listarProjetos: () => request('/projetos/'),
  listarProjetosDaEmpresa: (empresaId) => request(`/projetos/?empresa=${empresaId}`),
  buscarProjeto: (id) => request(`/projetos/${id}/`),
  criarProjeto: (dados) => post('/projetos/', dados),
  atualizarProjeto: (id, dados) => patch(`/projetos/${id}/`, dados),
  excluirProjeto: (id) => remover(`/projetos/${id}/`),

  // Membros
  listarMembros: () => request('/membros/'),
  buscarMembro: (id) => request(`/membros/${id}/`),
  criarMembro: (dados) => post('/membros/', dados),
  atualizarMembro: (id, dados) => patch(`/membros/${id}/`, dados),
  excluirMembro: (id) => remover(`/membros/${id}/`),

  // Alocações (equipe dos projetos)
  listarAlocacoesDoProjeto: (projetoId) => request(`/alocacoes/?projeto=${projetoId}`),
  listarAlocacoesDoMembro: (membroId) => request(`/alocacoes/?membro=${membroId}`),
  criarAlocacao: (dados) => post('/alocacoes/', dados),
  atualizarAlocacao: (id, dados) => patch(`/alocacoes/${id}/`, dados),
  excluirAlocacao: (id) => remover(`/alocacoes/${id}/`),
}
