import { Link, useParams } from 'react-router-dom'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useApi } from '../hooks/useApi.js'
import { api } from '../services/api.js'
import { formatarData } from '../utils/formatar.js'

export default function EmpresaProjetosPage() {
  const { id } = useParams()

  // Busca empresa e projetos em paralelo
  const { dados, carregando, erro } = useApi(
    () => Promise.all([api.buscarEmpresa(id), api.listarProjetosDaEmpresa(id)]),
    [id],
  )
  const [empresa, projetos] = dados ?? []

  return (
    <section>
      <Link to="/projetos" className="voltar">
        ← Empresas parceiras
      </Link>

      {carregando && <Carregando />}
      {erro && <Erro mensagem={erro} />}

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
                <p className="projeto-card__datas">
                  {formatarData(projeto.data_inicio)} → {formatarData(projeto.data_fim_prevista)}
                </p>
              </Link>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
