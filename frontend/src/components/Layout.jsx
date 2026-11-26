import { Link, NavLink, Outlet } from 'react-router-dom'
import { NOMES_DOS_PAPEIS, useAuth } from '../auth/useAuth.js'
import Avatar from './Avatar.jsx'

export default function Layout() {
  const { usuario, sair } = useAuth()

  return (
    <div className="app">
      <header className="topbar">
        <div className="container topbar__conteudo">
          <NavLink to="/" className="marca" aria-label="NEO — página inicial">
            <img src="/logos/neo.svg" alt="" className="marca__logo" />
          </NavLink>

          <nav className="menu">
            <NavLink to="/" end className="menu__link">
              Home
            </NavLink>
            <NavLink to="/projetos" className="menu__link">
              Projetos
            </NavLink>
            <NavLink to="/membros" className="menu__link">
              Membros
            </NavLink>
          </nav>

          <div className="usuario">
            <Link
              to={usuario.membro ? `/membros/${usuario.membro.id}` : '/'}
              className="usuario__perfil"
              title="Meu perfil"
            >
              <Avatar nome={usuario.nome} fotoUrl={usuario.membro?.foto_url} tamanho={32} />
              <span className="usuario__nome">{usuario.membro?.sigla ?? usuario.nome}</span>
              <span className={`papel papel--${usuario.papel}`}>{NOMES_DOS_PAPEIS[usuario.papel]}</span>
            </Link>
            <button type="button" className="botao botao--fantasma botao--pequeno" onClick={sair}>
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="container conteudo">
        <Outlet />
      </main>
    </div>
  )
}
