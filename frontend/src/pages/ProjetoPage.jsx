import { Link, useParams } from 'react-router-dom'
import Avatar from '../components/Avatar.jsx'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useApi } from '../hooks/useApi.js'
import { api } from '../services/api.js'
import { formatarData, formatarDuracao } from '../utils/formatar.js'

export default function ProjetoPage() {
  const { id } = useParams()

  // Projeto e equipe em paralelo; a empresa (para a logo) vem em seguida
  const { dados, carregando, erro } = useApi(async () => {
    const [projeto, alocacoes] = await Promise.all([
      api.buscarProjeto(id),
      api.listarAlocacoesDoProjeto(id),
    ])
    const empresa = await api.buscarEmpresa(projeto.empresa)
    return { projeto, alocacoes, empresa }
  }, [id])

  if (carregando) return <Carregando />
  if (erro) return <Erro mensagem={erro} />

  const { projeto, alocacoes, empresa } = dados
  const duracao = formatarDuracao(projeto.data_inicio, projeto.data_fim_prevista)

  return (
    <section>
      <Link to={`/projetos/empresa/${empresa.id}`} className="voltar">
        ← Projetos com {empresa.nome}
      </Link>

      <header className="projeto-cabecalho">
        <div className="projeto-cabecalho__titulo">
          <h1>{projeto.nome}</h1>
          <StatusBadge status={projeto.status} texto={projeto.status_display} />
        </div>

        <Link to={`/projetos/empresa/${empresa.id}`} className="projeto-cabecalho__empresa">
          {empresa.logo_url && <img src={empresa.logo_url} alt="" className="logo-branca" />}
          <span>{empresa.nome}</span>
        </Link>
      </header>

      {projeto.descricao && <p className="projeto-descricao">{projeto.descricao}</p>}

      <dl className="projeto-infos">
        <div>
          <dt>Início</dt>
          <dd>{formatarData(projeto.data_inicio)}</dd>
        </div>
        <div>
          <dt>Fim previsto</dt>
          <dd>{formatarData(projeto.data_fim_prevista)}</dd>
        </div>
        {duracao && (
          <div>
            <dt>Duração</dt>
            <dd>{duracao}</dd>
          </div>
        )}
        <div>
          <dt>Equipe</dt>
          <dd>
            {alocacoes.length} {alocacoes.length === 1 ? 'membro' : 'membros'}
          </dd>
        </div>
      </dl>

      <h2 className="titulo-secao">Equipe</h2>

      {alocacoes.length === 0 ? (
        <Vazio texto="Nenhum membro alocado neste projeto ainda." />
      ) : (
        <div className="grade-equipe">
          {alocacoes.map((alocacao) => (
            <article key={alocacao.id} className="membro-card">
              <Avatar nome={alocacao.membro_nome} fotoUrl={alocacao.membro_foto_url} />
              <div className="membro-card__nome">
                <h3>{alocacao.membro_nome}</h3>
                <span className="membro-card__sigla">{alocacao.membro_sigla}</span>
              </div>
              <p className="membro-card__funcao">{alocacao.funcao}</p>
              <span className="membro-card__escopo">{alocacao.escopo}</span>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
