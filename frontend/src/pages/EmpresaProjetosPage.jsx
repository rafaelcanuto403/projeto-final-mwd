import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import DescricaoProjeto from '../components/DescricaoProjeto.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { consultas, useConsultas, useExcluirEmpresa } from '../api/queries.js'
import { usePode } from '../auth/useAuth.js'

export default function EmpresaProjetosPage() {
  const { id } = useParams()
  const navegar = useNavigate()
  const pode = usePode()
  const [erroAcao, setErroAcao] = useState(null)
  const exclusao = useExcluirEmpresa()

  const { dados, carregando, erro } = useConsultas([consultas.empresa(id), consultas.projetosDaEmpresa(id)])
  const [empresa, projetos] = dados
  // Só mostra o conteúdo quando a empresa e os projetos dela chegaram.
  const pronto = !carregando && !erro

  async function excluirEmpresa() {
    if (!window.confirm(`Excluir a empresa ${empresa.nome}? Esta ação não pode ser desfeita.`)) return
    try {
      await exclusao.mutateAsync(empresa.id)
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

      {pronto && (
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
              {pode('empresa', 'editar') && (
                <Link to={`/projetos/empresa/${empresa.id}/editar`} className="botao botao--fantasma">
                  Editar
                </Link>
              )}
              {pode('empresa', 'excluir') && (
                <button type="button" className="botao botao--perigo" onClick={excluirEmpresa}>
                  Excluir
                </button>
              )}
              {pode('projeto', 'criar') && (
                <Link to={`/projetos/novo?empresa=${empresa.id}`} className="botao botao--primario">
                  + Novo projeto
                </Link>
              )}
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
                <DescricaoProjeto descricao={projeto.descricao} className="texto-suave" />
              </Link>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
