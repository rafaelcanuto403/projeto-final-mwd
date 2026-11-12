// URL base da API Django. Em desenvolvimento, o Vite repassa /api para 127.0.0.1:8000
// (ver vite.config.js). Pode ser trocada com a variável VITE_API_URL num arquivo .env
const API_URL = import.meta.env.VITE_API_URL ?? '/api'

async function request(caminho, opcoes = {}) {
  const resposta = await fetch(`${API_URL}${caminho}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opcoes,
  })

  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null)
    const mensagem = corpo?.detail ?? `Erro ${resposta.status} ao acessar a API.`
    throw new Error(mensagem)
  }

  return resposta.status === 204 ? null : resposta.json()
}

export const api = {
  listarEmpresas: () => request('/empresas/'),
  buscarEmpresa: (id) => request(`/empresas/${id}/`),
  listarProjetosDaEmpresa: (empresaId) => request(`/projetos/?empresa=${empresaId}`),
  buscarProjeto: (id) => request(`/projetos/${id}/`),
  listarAlocacoesDoProjeto: (projetoId) => request(`/alocacoes/?projeto=${projetoId}`),
}
