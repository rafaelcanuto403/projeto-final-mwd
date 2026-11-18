import axios from 'axios'
import { useCallback, useEffect, useState } from 'react'

const cliente = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
})

export class ApiError extends Error {
  constructor(mensagem, campos = {}) {
    super(mensagem)
    this.campos = campos
  }
}

async function request(caminho, { metodo = 'GET', corpo } = {}) {
  try {
    const resposta = await cliente.request({ url: caminho, method: metodo, data: corpo })
    return resposta.status === 204 ? null : resposta.data
  } catch (erro) {
    if (!axios.isAxiosError(erro)) throw erro
    if (!erro.response) throw new ApiError('Não foi possível conectar à API.')

    const { status, data: dados } = erro.response
    if (dados?.detail) throw new ApiError(dados.detail)
    if (dados && typeof dados === 'object') {
      throw new ApiError('Verifique os campos destacados.', dados)
    }
    throw new ApiError(`Erro ${status} ao acessar a API.`)
  }
}

const enviar = (metodo) => (caminho, corpo) => request(caminho, { metodo, corpo })
const post = enviar('POST')
const patch = enviar('PATCH')
const remover = (caminho) => request(caminho, { metodo: 'DELETE' })

export const api = {
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
}

export function useApi(buscar, dependencias = []) {
  const [estado, setEstado] = useState({ dados: null, carregando: true, erro: null })
  const [versao, setVersao] = useState(0)

  // oxlint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    let ativo = true
    setEstado((anterior) => ({ ...anterior, carregando: anterior.dados === null, erro: null }))

    buscar()
      .then((dados) => ativo && setEstado({ dados, carregando: false, erro: null }))
      .catch((erro) => ativo && setEstado({ dados: null, carregando: false, erro: erro.message }))

    return () => {
      ativo = false
    }
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencias, versao])

  const recarregar = useCallback(() => setVersao((v) => v + 1), [])

  return { ...estado, recarregar }
}
