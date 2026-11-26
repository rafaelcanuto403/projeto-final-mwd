const CHAVE = 'neo.tokens'

export function lerTokens() {
  try {
    return JSON.parse(localStorage.getItem(CHAVE)) ?? {}
  } catch {
    return {}
  }
}

export function salvarTokens({ access, refresh }) {
  localStorage.setItem(CHAVE, JSON.stringify({ access, refresh }))
}

export function limparTokens() {
  localStorage.removeItem(CHAVE)
}
