import { NavLink, Outlet } from 'react-router-dom'

export default function Layout() {
  return (
    <div className="app">
      <header className="topbar">
        <div className="container topbar__conteudo">
          <NavLink to="/" className="marca">
            <img src="/logos/neo.svg" alt="" className="marca__logo" />
            <span>NEO</span>
          </NavLink>

          <nav className="menu">
            <NavLink to="/projetos" className="menu__link">
              Projetos
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
