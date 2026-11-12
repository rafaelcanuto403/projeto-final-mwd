import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import EmpresaFormPage from './pages/EmpresaFormPage.jsx'
import EmpresaProjetosPage from './pages/EmpresaProjetosPage.jsx'
import EmpresasPage from './pages/EmpresasPage.jsx'
import InicioPage from './pages/InicioPage.jsx'
import MembroFormPage from './pages/MembroFormPage.jsx'
import MembroPage from './pages/MembroPage.jsx'
import MembrosPage from './pages/MembrosPage.jsx'
import NaoEncontrada from './pages/NaoEncontrada.jsx'
import ProjetoFormPage from './pages/ProjetoFormPage.jsx'
import ProjetoPage from './pages/ProjetoPage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<InicioPage />} />

          {/* Empresas parceiras */}
          <Route path="projetos" element={<EmpresasPage />} />
          <Route path="projetos/empresa/nova" element={<EmpresaFormPage />} />
          <Route path="projetos/empresa/:id" element={<EmpresaProjetosPage />} />
          <Route path="projetos/empresa/:id/editar" element={<EmpresaFormPage />} />

          {/* Projetos */}
          <Route path="projetos/novo" element={<ProjetoFormPage />} />
          <Route path="projetos/:id" element={<ProjetoPage />} />
          <Route path="projetos/:id/editar" element={<ProjetoFormPage />} />

          {/* Membros */}
          <Route path="membros" element={<MembrosPage />} />
          <Route path="membros/novo" element={<MembroFormPage />} />
          <Route path="membros/:id" element={<MembroPage />} />
          <Route path="membros/:id/editar" element={<MembroFormPage />} />

          <Route path="*" element={<NaoEncontrada />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
