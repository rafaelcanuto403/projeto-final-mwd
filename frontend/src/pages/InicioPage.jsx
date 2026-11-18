import { Link } from 'react-router-dom'
import EmpresaCard from '../components/EmpresaCard.jsx'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { api, useApi } from '../api/useApi.js'

export default function InicioPage() {
  const { dados, carregando, erro } = useApi(() =>
    Promise.all([api.listarEmpresas(), api.listarProjetos(), api.listarMembros()]),
  )

  if (carregando) return <Carregando />
  if (erro) return <Erro mensagem={erro} />

  const [empresas, projetos, membros] = dados
  const doStatus = (status) => projetos.filter((p) => p.status === status)
  const emAndamento = doStatus('em_andamento')
  const emPlanejamento = doStatus('planejamento').sort((a, b) => a.data_inicio.localeCompare(b.data_inicio))

  return (
    <>
      <section className="inicio-hero">
        <h1>Hub de Projetos</h1>
        <p className="inicio-hero__texto">Acompanhamento de projetos do NEO Empresarial</p>
        <div className="acoes">
          <Link to="/projetos" className="botao botao--primario">
            Ver projetos
          </Link>
          <Link to="/membros" className="botao botao--fantasma">
            Ver membros
          </Link>
        </div>
      </section>

      <dl className="projeto-infos inicio-numeros">
        <div>
          <dt>Empresas parceiras</dt>
          <dd>{empresas.length}</dd>
        </div>
        <div>
          <dt>Projetos</dt>
          <dd>{projetos.length}</dd>
        </div>
        <div>
          <dt>Em andamento</dt>
          <dd>{emAndamento.length}</dd>
        </div>
        <div>
          <dt>Membros</dt>
          <dd>{membros.length}</dd>
        </div>
      </dl>

      <ListaResumo titulo="Em andamento" projetos={emAndamento} vazio="Nenhum projeto em andamento no momento." />
      <ListaResumo titulo="Backlog" projetos={emPlanejamento} vazio="Nenhum projeto em planejamento." />

      <section className="inicio-secao">
        <div className="secao-cabecalho">
          <h2 className="titulo-secao">Empresas parceiras</h2>
          <Link to="/projetos" className="link-secao">
            Ver todas →
          </Link>
        </div>
        <div className="grade-empresas">
          {empresas.map((empresa) => (
            <EmpresaCard key={empresa.id} empresa={empresa} />
          ))}
        </div>
      </section>
    </>
  )
}

function ListaResumo({ titulo, projetos, vazio }) {
  return (
    <section className="inicio-secao">
      <h2 className="titulo-secao">{titulo}</h2>
      {projetos.length === 0 ? (
        <Vazio texto={vazio} />
      ) : (
        <div className="lista-projetos">
          {projetos.map((projeto) => (
            <Link key={projeto.id} to={`/projetos/${projeto.id}`} className="projeto-card">
              <div className="projeto-card__topo">
                <h3>{projeto.nome}</h3>
                <StatusBadge status={projeto.status} texto={projeto.status_display} />
              </div>
              <div className="projeto-card__empresa">
                {projeto.empresa_logo_url && <img src={projeto.empresa_logo_url} alt="" className="logo-branca" />}
                <span>{projeto.empresa_nome}</span>
              </div>
              {projeto.descricao && <p className="texto-suave">{projeto.descricao}</p>}
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
