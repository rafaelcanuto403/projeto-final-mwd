import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import EmpresaProjetosPage from './pages/EmpresaProjetosPage.jsx'
import EmpresasPage from './pages/EmpresasPage.jsx'
import ProjetoPage from './pages/ProjetoPage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          {/* Por enquanto a página inicial leva direto para Projetos */}
          <Route index element={<Navigate to="/projetos" replace />} />
          <Route path="projetos" element={<EmpresasPage />} />
          <Route path="projetos/empresa/:id" element={<EmpresaProjetosPage />} />
          <Route path="projetos/:id" element={<ProjetoPage />} />
          <Route path="*" element={<p className="estado">Página não encontrada.</p>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
