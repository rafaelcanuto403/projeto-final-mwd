import { createContext, useContext } from 'react'

export const AuthContext = createContext(null)

export const NOMES_DOS_PAPEIS = { admin: 'Admin', membro: 'Membro' }

export function useAuth() {
  return useContext(AuthContext)
}

/** Permissões globais vindas de /api/auth/me/ — ex.: pode('empresa', 'criar'). */
export function usePode() {
  const { usuario } = useAuth()
  return (recurso, acao) => Boolean(usuario?.permissoes?.[recurso]?.[acao])
}
