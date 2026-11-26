import { queryOptions, useMutation, useQueries, useQueryClient } from '@tanstack/react-query'
import { api, salvarArquivo } from './cliente.js'

/**
 * Chaves do cache. São hierárquicas: invalidar ['projetos'] atualiza a lista, os detalhes e os
 * projetos por empresa de uma vez. Ids viram string para '/projetos/5' (da URL) e 5 (da API)
 * caírem na mesma entrada.
 */
export const chaves = {
  empresas: () => ['empresas'],
  empresa: (id) => ['empresas', String(id)],
  projetos: () => ['projetos'],
  projetosDaEmpresa: (empresaId) => ['projetos', { empresa: String(empresaId) }],
  projeto: (id) => ['projetos', String(id)],
  membros: () => ['membros'],
  membro: (id) => ['membros', String(id)],
  alocacoes: (filtro = {}) => ['alocacoes', filtro],
  documentos: () => ['documentos'],
  documentosDoProjeto: (projetoId) => ['documentos', { projeto: String(projetoId) }],
  previa: (documento) => ['arquivos', documento.id, 'previa'],
  arquivo: (documento) => ['arquivos', documento.id, 'completo'],
}

// O tipo do arquivo vem da extensão (a mesma lista que o backend aceita), nunca do conteúdo:
// assim um arquivo malicioso não consegue ser aberto pelo navegador como uma página HTML.
const TIPOS = { pdf: 'application/pdf', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg' }

export const extensaoDe = (documento) => documento.nome_arquivo?.split('.').pop()?.toLowerCase() ?? ''

async function comUrl(promessaDeBlob, tipo) {
  let blob = await promessaDeBlob
  if (tipo) blob = new Blob([blob], { type: tipo })
  return { blob, url: URL.createObjectURL(blob) }
}

export const consultas = {
  empresas: () => queryOptions({ queryKey: chaves.empresas(), queryFn: api.listarEmpresas }),
  empresa: (id) => queryOptions({ queryKey: chaves.empresa(id), queryFn: () => api.buscarEmpresa(id) }),

  projetos: () => queryOptions({ queryKey: chaves.projetos(), queryFn: api.listarProjetos }),
  projetosDaEmpresa: (empresaId) =>
    queryOptions({
      queryKey: chaves.projetosDaEmpresa(empresaId),
      queryFn: () => api.listarProjetosDaEmpresa(empresaId),
    }),
  projeto: (id) => queryOptions({ queryKey: chaves.projeto(id), queryFn: () => api.buscarProjeto(id) }),

  membros: () => queryOptions({ queryKey: chaves.membros(), queryFn: api.listarMembros }),
  membro: (id) => queryOptions({ queryKey: chaves.membro(id), queryFn: () => api.buscarMembro(id) }),

  alocacoes: () => queryOptions({ queryKey: chaves.alocacoes(), queryFn: api.listarAlocacoes }),
  alocacoesDoProjeto: (projetoId) =>
    queryOptions({
      queryKey: chaves.alocacoes({ projeto: String(projetoId) }),
      queryFn: () => api.listarAlocacoesDoProjeto(projetoId),
    }),
  alocacoesDoMembro: (membroId) =>
    queryOptions({
      queryKey: chaves.alocacoes({ membro: String(membroId) }),
      queryFn: () => api.listarAlocacoesDoMembro(membroId),
    }),

  documentosDoProjeto: (projetoId) =>
    queryOptions({
      queryKey: chaves.documentosDoProjeto(projetoId),
      queryFn: () => api.listarDocumentosDoProjeto(projetoId),
    }),

  // A prévia só muda se o arquivo mudar, e aí o documento é outro: nunca fica "velha".
  previa: (documento) =>
    queryOptions({
      queryKey: chaves.previa(documento),
      queryFn: () => comUrl(api.previaDocumento(documento)),
      staleTime: Infinity,
      gcTime: 30 * 60_000,
    }),

  // Arquivo completo (até 20 MB): fica pouco tempo em memória depois que ninguém usa. O mesmo
  // cache serve o visualizador e o botão de baixar (abrir e depois baixar não baixa duas vezes).
  arquivo: (documento) =>
    queryOptions({
      queryKey: chaves.arquivo(documento),
      queryFn: () => comUrl(api.abrirDocumento(documento), TIPOS[extensaoDe(documento)] ?? 'application/octet-stream'),
      staleTime: Infinity,
      gcTime: 60_000,
    }),
}

/** Baixar um documento reaproveitando o arquivo se ele já estiver no cache. */
export function useBaixarDocumento() {
  const queryClient = useQueryClient()
  return async (documento) => {
    const { blob } = await queryClient.fetchQuery(consultas.arquivo(documento))
    salvarArquivo(blob, documento.nome_arquivo)
  }
}

/** Várias consultas na mesma tela: um único estado de carregando/erro para a página. */
export function useConsultas(lista) {
  return useQueries({
    queries: lista,
    combine: (resultados) => ({
      dados: resultados.map((r) => r.data),
      carregando: resultados.some((r) => r.isPending),
      erro: resultados.find((r) => r.error)?.error?.message ?? null,
    }),
  })
}

// ---- mutações: cada uma invalida só o que ela pode ter mudado ------------------------

/**
 * `afetadas`: listas que podem ter mudado (são buscadas de novo).
 * `excluidas(id)`: entradas do item excluído; saem do cache *antes* de invalidar, senão a tela
 * ainda aberta tentaria buscar de novo algo que não existe mais (e mostraria um 404).
 */
function useMutacao(mutationFn, afetadas, excluidas = () => []) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: (_resposta, variaveis) => {
      for (const queryKey of excluidas(variaveis)) queryClient.removeQueries({ queryKey })
      return Promise.all(afetadas.map((queryKey) => queryClient.invalidateQueries({ queryKey })))
    },
  })
}

// Empresas aparecem nos projetos (nome e logo) e projetos contam nas empresas.
const EMPRESAS_E_PROJETOS = [chaves.empresas(), chaves.projetos()]
// Projetos aparecem nas alocações (nome, status) e excluir um projeto leva equipe e documentos.
const PROJETOS_E_RELACIONADOS = [chaves.projetos(), chaves.empresas(), chaves.alocacoes(), chaves.documentos()]
// Membros aparecem nas alocações; passar um cargo muda outro membro também.
const MEMBROS_E_ALOCACOES = [chaves.membros(), chaves.alocacoes()]
// A equipe muda contagens de membros e as permissões de cada projeto (função de gerente).
const EQUIPE = [chaves.alocacoes(), chaves.membros(), chaves.projetos()]

export const useSalvarEmpresa = () =>
  useMutacao(({ id, dados }) => (id ? api.atualizarEmpresa(id, dados) : api.criarEmpresa(dados)), EMPRESAS_E_PROJETOS)
export const useExcluirEmpresa = () =>
  useMutacao(api.excluirEmpresa, EMPRESAS_E_PROJETOS, (id) => [chaves.empresa(id), chaves.projetosDaEmpresa(id)])

export const useSalvarProjeto = () =>
  useMutacao(({ id, dados }) => (id ? api.atualizarProjeto(id, dados) : api.criarProjeto(dados)), PROJETOS_E_RELACIONADOS)
export const useExcluirProjeto = () =>
  useMutacao(api.excluirProjeto, PROJETOS_E_RELACIONADOS, (id) => [
    chaves.projeto(id),
    chaves.alocacoes({ projeto: String(id) }),
    chaves.documentosDoProjeto(id),
  ])

export const useSalvarMembro = () =>
  useMutacao(({ id, dados }) => (id ? api.atualizarMembro(id, dados) : api.criarMembro(dados)), MEMBROS_E_ALOCACOES)
export const useExcluirMembro = () =>
  useMutacao(api.excluirMembro, MEMBROS_E_ALOCACOES, (id) => [chaves.membro(id), chaves.alocacoes({ membro: String(id) })])

export const useSalvarAlocacao = () =>
  useMutacao(({ id, dados }) => (id ? api.atualizarAlocacao(id, dados) : api.criarAlocacao(dados)), EQUIPE)
export const useExcluirAlocacao = () => useMutacao(api.excluirAlocacao, EQUIPE)

export const useEnviarDocumento = () => useMutacao(api.enviarDocumento, [chaves.documentos()])
export const useExcluirDocumento = () =>
  useMutacao(api.excluirDocumento, [chaves.documentos()], (id) => [['arquivos', id]])
