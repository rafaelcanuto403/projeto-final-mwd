import { useCallback, useEffect, useMemo, useState } from 'react'
import { SESSAO_EXPIRADA, api } from '../api/cliente.js'
import { queryClient } from '../api/queryClient.js'
import { limparTokens, lerTokens, salvarTokens } from '../api/tokens.js'
import { AuthContext } from './useAuth.js'

// O cache guarda o que a API mostrou para *este* usuário (documentos, permissões de cada
// projeto...). Ao trocar de usuário ele é descartado, para nada de uma sessão aparecer na outra.
function limparSessao() {
  limparTokens()
  queryClient.clear()
}

async function buscarUsuario() {
  try {
    return await api.eu()
  } catch {
    limparSessao()
    return null
  }
}

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [carregando, setCarregando] = useState(() => Boolean(lerTokens().access))

  useEffect(() => {
    let ativo = true
    if (lerTokens().access) {
      buscarUsuario().then((encontrado) => {
        if (!ativo) return
        setUsuario(encontrado)
        setCarregando(false)
      })
    }

    const expirou = () => {
      queryClient.clear()
      setUsuario(null)
    }
    window.addEventListener(SESSAO_EXPIRADA, expirou)
    return () => {
      ativo = false
      window.removeEventListener(SESSAO_EXPIRADA, expirou)
    }
  }, [])

  const recarregarUsuario = useCallback(async () => setUsuario(await buscarUsuario()), [])

  const entrar = useCallback(async (email, senha) => {
    const tokens = await api.entrar(email, senha)
    queryClient.clear()
    salvarTokens(tokens)
    setUsuario(await buscarUsuario())
  }, [])

  const sair = useCallback(() => {
    limparSessao()
    setUsuario(null)
  }, [])

  const valor = useMemo(
    () => ({ usuario, carregando, entrar, sair, recarregarUsuario }),
    [usuario, carregando, entrar, sair, recarregarUsuario],
  )

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}
