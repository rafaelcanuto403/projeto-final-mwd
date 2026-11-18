import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { api, useApi } from '../api/useApi.js'

export default function EmpresaProjetosPage() {
  const { id } = useParams()
  const navegar = useNavigate()
  const [erroAcao, setErroAcao] = useState(null)

  const { dados, carregando, erro } = useApi(
    () => Promise.all([api.buscarEmpresa(id), api.listarProjetosDaEmpresa(id)]),
    [id],
  )
  const [empresa, projetos] = dados ?? []

  async function excluirEmpresa() {
    if (!window.confirm(`Excluir a empresa ${empresa.nome}? Esta ação não pode ser desfeita.`)) return
    try {
      await api.excluirEmpresa(empresa.id)
      navegar('/projetos')
    } catch (e) {
      setErroAcao(e.message)
    }
  }

  return (
    <section>
      <Link to="/projetos" className="voltar">
        ← Empresas parceiras
      </Link>

      {carregando && <Carregando />}
      {erro && <Erro mensagem={erro} />}
      {erroAcao && <p className="alerta alerta--erro">{erroAcao}</p>}

      {empresa && (
        <>
          <header className="cabecalho-empresa">
            {empresa.logo_url && (
              <div className="cabecalho-empresa__logo">
                <img src={empresa.logo_url} alt="" className="logo-branca" />
              </div>
            )}
            <div>
              <h1>{empresa.nome}</h1>
              <p className="texto-suave">
                {empresa.total_projetos} {empresa.total_projetos === 1 ? 'projeto' : 'projetos'} com o NEO
              </p>
            </div>

            <div className="acoes acoes--direita">
              <Link to={`/projetos/empresa/${empresa.id}/editar`} className="botao botao--fantasma">
                Editar
              </Link>
              <button type="button" className="botao botao--perigo" onClick={excluirEmpresa}>
                Excluir
              </button>
              <Link to={`/projetos/novo?empresa=${empresa.id}`} className="botao botao--primario">
                + Novo projeto
              </Link>
            </div>
          </header>

          {projetos.length === 0 && <Vazio texto="Nenhum projeto com esta empresa ainda." />}

          <div className="lista-projetos">
            {projetos.map((projeto) => (
              <Link key={projeto.id} to={`/projetos/${projeto.id}`} className="projeto-card">
                <div className="projeto-card__topo">
                  <h3>{projeto.nome}</h3>
                  <StatusBadge status={projeto.status} texto={projeto.status_display} />
                </div>
                {projeto.descricao && <p className="texto-suave">{projeto.descricao}</p>}
              </Link>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
