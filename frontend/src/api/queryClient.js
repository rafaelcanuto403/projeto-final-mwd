import { QueryClient } from '@tanstack/react-query'

// Erros que não melhoram tentando de novo: validação, sem login, sem permissão, não existe.
const SEM_NOVA_TENTATIVA = new Set([400, 401, 403, 404])

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Por 30 s os dados em cache são considerados atuais: navegar entre páginas não refaz as
      // requisições. Depois disso, a tela mostra o cache na hora e atualiza em segundo plano.
      staleTime: 30_000,
      retry: (falhas, erro) => !SEM_NOVA_TENTATIVA.has(erro?.status) && falhas < 3,
      retryDelay: (tentativa) => [1000, 3000, 8000][tentativa] ?? 8000,
    },
  },
})

// Arquivos baixados (documentos e prévias) ficam no cache como { blob, url }, com uma URL
// "blob:" para usar em <img>/<iframe>. Quando o TanStack Query descarta a entrada do cache,
// a URL é liberada junto — assim a memória dos arquivos dura exatamente o tempo do cache.
queryClient.getQueryCache().subscribe((evento) => {
  if (evento.type !== 'removed') return
  const url = evento.query.state.data?.url
  if (typeof url === 'string' && url.startsWith('blob:')) URL.revokeObjectURL(url)
})
