import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import Campo from '../components/Campo.jsx'
import { useAuth } from '../auth/useAuth.js'

export default function LoginPage() {
  const { usuario, entrar } = useAuth()
  const navegar = useNavigate()
  const destino = useLocation().state?.de ?? '/'
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState(null)
  const [enviando, setEnviando] = useState(false)

  if (usuario) return <Navigate to={destino} replace />

  async function enviar(evento) {
    evento.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      await entrar(email.trim(), senha)
      navegar(destino, { replace: true })
    } catch (e) {
      setErro(e.message)
      setEnviando(false)
    }
  }

  return (
    <main className="login">
      <div className="login__conteudo">
        <form className="login__cartao formulario" onSubmit={enviar}>
          <img src="/logos/neo.svg" alt="NEO" className="login__logo" />
          <div className="login__titulo">
            <h1>Hub de Projetos</h1>
            <p className="texto-suave">Acesso exclusivo para membros do NEO.</p>
          </div>

          {erro && <p className="alerta alerta--erro">{erro}</p>}

          <Campo rotulo="E-mail" nome="email">
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </Campo>
          <Campo rotulo="Senha" nome="senha">
            <input
              id="senha"
              type="password"
              autoComplete="current-password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
            />
          </Campo>

          <button type="submit" className="botao botao--primario" disabled={enviando}>
            {enviando ? 'Entrando...' : 'Entrar'}
          </button>
        </form>

        <h2 className="login__frase">
          Mentes brilhantes <span className="login__frase-destaque">crescem juntas</span>
        </h2>
      </div>
    </main>
  )
}
