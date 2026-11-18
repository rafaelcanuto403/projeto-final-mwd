import { NavLink, Outlet } from 'react-router-dom'

export default function Layout() {
  return (
    <div className="app">
      <header className="topbar">
        <div className="container topbar__conteudo">
          <NavLink to="/" className="marca" aria-label="NEO — página inicial">
            <img src="/logos/neo.svg" alt="" className="marca__logo" />
            <p>Mentes Brilhantes Crescem Juntas</p>
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
        </div>
      </header>

      <main className="container conteudo">
        <Outlet />
      </main>
    </div>
  )
}
