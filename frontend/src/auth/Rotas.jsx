import { Link, Navigate, Outlet, useLocation } from 'react-router-dom'
import { Carregando } from '../components/Estado.jsx'
import { useAuth } from './useAuth.js'

/** Só deixa passar quem está logado; senão manda para o login lembrando a página pedida. */
export function RotaProtegida() {
  const { usuario, carregando } = useAuth()
  const local = useLocation()

  if (carregando) return <Carregando />
  if (!usuario) return <Navigate to="/login" replace state={{ de: local.pathname + local.search }} />
  return <Outlet />
}

/** Bloqueia a página inteira quando a permissão (global ou do objeto) não existe. */
export function ExigePermissao({ permitido, children }) {
  return permitido ? children : <SemPermissao />
}

export function SemPermissao() {
  return (
    <section className="sem-permissao">
      <h1>Sem permissão</h1>
      <p className="texto-suave">O seu papel não permite acessar esta página ou realizar esta ação.</p>
      <Link to="/" className="botao botao--fantasma">
        Voltar para o início
      </Link>
    </section>
  )
}
