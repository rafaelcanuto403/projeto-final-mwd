import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext.jsx'
import { usePode } from './auth/useAuth.js'
import { ExigePermissao, RotaProtegida } from './auth/Rotas.jsx'
import Layout from './components/Layout.jsx'
import EmpresaFormPage from './pages/EmpresaFormPage.jsx'
import EmpresaProjetosPage from './pages/EmpresaProjetosPage.jsx'
import EmpresasPage from './pages/EmpresasPage.jsx'
import InicioPage from './pages/InicioPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import MembroFormPage from './pages/MembroFormPage.jsx'
import MembroPage from './pages/MembroPage.jsx'
import MembrosPage from './pages/MembrosPage.jsx'
import NaoEncontrada from './pages/NaoEncontrada.jsx'
import ProjetoFormPage from './pages/ProjetoFormPage.jsx'
import ProjetoPage from './pages/ProjetoPage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Rotas />
      </AuthProvider>
    </BrowserRouter>
  )
}

function Rotas() {
  const pode = usePode()
  const exige = (recurso, acao, pagina) => (
    <ExigePermissao permitido={pode(recurso, acao)}>{pagina}</ExigePermissao>
  )

  return (
    <Routes>
      <Route path="login" element={<LoginPage />} />

      <Route element={<RotaProtegida />}>
        <Route element={<Layout />}>
          <Route index element={<InicioPage />} />

          <Route path="projetos" element={<EmpresasPage />} />
          <Route path="projetos/empresa/nova" element={exige('empresa', 'criar', <EmpresaFormPage />)} />
          <Route path="projetos/empresa/:id" element={<EmpresaProjetosPage />} />
          <Route path="projetos/empresa/:id/editar" element={exige('empresa', 'editar', <EmpresaFormPage />)} />

          <Route path="projetos/novo" element={exige('projeto', 'criar', <ProjetoFormPage />)} />
          <Route path="projetos/:id" element={<ProjetoPage />} />
          <Route path="projetos/:id/editar" element={<ProjetoFormPage />} />

          <Route path="membros" element={<MembrosPage />} />
          <Route path="membros/novo" element={exige('membro', 'criar', <MembroFormPage />)} />
          <Route path="membros/:id" element={<MembroPage />} />
          <Route path="membros/:id/editar" element={<MembroFormPage />} />

          <Route path="*" element={<NaoEncontrada />} />
        </Route>
      </Route>
    </Routes>
  )
}
