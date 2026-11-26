import axios from 'axios'

import { limparTokens, lerTokens, salvarTokens } from './tokens.js'

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'
const cliente = axios.create({ baseURL: BASE_URL })

export const SESSAO_EXPIRADA = 'neo:sessao-expirada'

cliente.interceptors.request.use((config) => {
  const { access } = lerTokens()
  if (access && !config.semToken) config.headers.Authorization = `Bearer ${access}`
  return config
})

// Vários pedidos podem receber 401 ao mesmo tempo: todos esperam o mesmo refresh.
let renovando = null

async function renovarAccess() {
  const { refresh } = lerTokens()
  if (!refresh) throw new Error('sem refresh token')
  const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh })
  salvarTokens({ access: data.access, refresh: data.refresh ?? refresh })
  return data.access
}

cliente.interceptors.response.use(undefined, async (erro) => {
  const config = erro.config
  if (erro.response?.status !== 401 || !config || config.semToken || config._tentouRenovar) {
    throw erro
  }
  config._tentouRenovar = true
  try {
    renovando ??= renovarAccess().finally(() => {
      renovando = null
    })
    await renovando
  } catch {
    limparTokens()
    window.dispatchEvent(new Event(SESSAO_EXPIRADA))
    throw erro
  }
  return cliente.request(config)
})

export class ApiError extends Error {
  constructor(mensagem, campos = {}, status = null) {
    super(mensagem)
    this.campos = campos
    this.status = status
  }
}

async function request(caminho, { metodo = 'GET', corpo, ...opcoes } = {}) {
  try {
    const resposta = await cliente.request({ url: caminho, method: metodo, data: corpo, ...opcoes })
    return resposta.status === 204 ? null : resposta.data
  } catch (erro) {
    if (!axios.isAxiosError(erro)) throw erro
    if (!erro.response) throw new ApiError('Não foi possível conectar à API.')

    const { status } = erro.response
    let dados = erro.response.data
    if (dados instanceof Blob) dados = JSON.parse((await dados.text()) || 'null')
    if (status === 401 && !opcoes.semToken) throw new ApiError('Sua sessão expirou. Entre novamente.', {}, status)
    if (dados?.detail) throw new ApiError(dados.detail, {}, status)
    if (dados && typeof dados === 'object') {
      throw new ApiError('Verifique os campos destacados.', dados, status)
    }
    throw new ApiError(`Erro ${status} ao acessar a API.`, {}, status)
  }
}

export function salvarArquivo(blob, nomeArquivo) {
  const url = URL.createObjectURL(blob)
  const link = Object.assign(document.createElement('a'), { href: url, download: nomeArquivo })
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

const enviar = (metodo) => (caminho, corpo) => request(caminho, { metodo, corpo })
const post = enviar('POST')
const patch = enviar('PATCH')
const remover = (caminho) => request(caminho, { metodo: 'DELETE' })

export const api = {
  entrar: (email, senha) => request('/auth/login/', { metodo: 'POST', corpo: { email, senha }, semToken: true }),
  eu: () => request('/auth/me/'),

  listarEmpresas: () => request('/empresas/'),
  buscarEmpresa: (id) => request(`/empresas/${id}/`),
  criarEmpresa: (dados) => post('/empresas/', dados),
  atualizarEmpresa: (id, dados) => patch(`/empresas/${id}/`, dados),
  excluirEmpresa: (id) => remover(`/empresas/${id}/`),

  listarProjetos: () => request('/projetos/'),
  listarProjetosDaEmpresa: (empresaId) => request(`/projetos/?empresa=${empresaId}`),
  buscarProjeto: (id) => request(`/projetos/${id}/`),
  criarProjeto: (dados) => post('/projetos/', dados),
  atualizarProjeto: (id, dados) => patch(`/projetos/${id}/`, dados),
  excluirProjeto: (id) => remover(`/projetos/${id}/`),

  listarMembros: () => request('/membros/'),
  buscarMembro: (id) => request(`/membros/${id}/`),
  criarMembro: (dados) => post('/membros/', dados),
  atualizarMembro: (id, dados) => patch(`/membros/${id}/`, dados),
  excluirMembro: (id) => remover(`/membros/${id}/`),

  listarAlocacoes: () => request('/alocacoes/'),
  listarAlocacoesDoProjeto: (projetoId) => request(`/alocacoes/?projeto=${projetoId}`),
  listarAlocacoesDoMembro: (membroId) => request(`/alocacoes/?membro=${membroId}`),
  criarAlocacao: (dados) => post('/alocacoes/', dados),
  atualizarAlocacao: (id, dados) => patch(`/alocacoes/${id}/`, dados),
  excluirAlocacao: (id) => remover(`/alocacoes/${id}/`),

  listarDocumentosDoProjeto: (projetoId) => request(`/documentos/?projeto=${projetoId}`),
  enviarDocumento: (formData) => post('/documentos/', formData),
  excluirDocumento: (id) => remover(`/documentos/${id}/`),
  previaDocumento: (documento) => request(`/documentos/${documento.id}/previa/`, { responseType: 'blob' }),
  abrirDocumento: (documento) => request(`/documentos/${documento.id}/download/`, { responseType: 'blob' }),
  baixarDocumento: async (documento) => salvarArquivo(await api.abrirDocumento(documento), documento.nome_arquivo),
}
