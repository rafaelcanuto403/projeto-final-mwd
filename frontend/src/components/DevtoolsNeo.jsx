import { useState } from 'react'
import { ReactQueryDevtoolsPanel } from '@tanstack/react-query-devtools'

// Devtools do TanStack Query com a logo do NEO no lugar do botão padrão (que não aceita ícone próprio).
// O painel oficial abre por cima da parte de baixo da tela. Só existe em desenvolvimento (npm run dev).
export default function DevtoolsNeo() {
  const [aberto, setAberto] = useState(false)

  if (!import.meta.env.DEV) return null

  return aberto ? (
    <div className="devtools__painel">
      <ReactQueryDevtoolsPanel onClose={() => setAberto(false)} style={{ height: '100%' }} />
    </div>
  ) : (
    <button
      type="button"
      className="devtools__botao"
      onClick={() => setAberto(true)}
      aria-label="Abrir o TanStack Query Devtools"
      title="TanStack Query Devtools"
    >
      <img src="/logos/neo.svg" alt="" />
    </button>
  )
}
