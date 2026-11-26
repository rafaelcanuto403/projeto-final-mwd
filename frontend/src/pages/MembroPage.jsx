import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Avatar from '../components/Avatar.jsx'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { consultas, useConsultas, useExcluirMembro } from '../api/queries.js'

const ORDEM_STATUS = { em_andamento: 0, planejamento: 1, concluido: 2 }

export default function MembroPage() {
  const { id } = useParams()
  const navegar = useNavigate()
  const [erroAcao, setErroAcao] = useState(null)
  const exclusao = useExcluirMembro()

  const { dados, carregando, erro } = useConsultas([consultas.membro(id), consultas.alocacoesDoMembro(id)])

  if (carregando) return <Carregando />
  if (erro) return <Erro mensagem={erro} />

  const [membro, alocacoes] = dados
  const ordenadas = [...alocacoes].sort(
    (a, b) =>
      ORDEM_STATUS[a.projeto_status] - ORDEM_STATUS[b.projeto_status] ||
      b.projeto_data_inicio.localeCompare(a.projeto_data_inicio),
  )
  const contar = (status) => alocacoes.filter((a) => a.projeto_status === status).length

  async function excluirMembro() {
    const aviso =
      alocacoes.length > 0
        ? ` Ele(a) também será removido(a) da equipe de ${alocacoes.length} projeto(s).`
        : ''
    if (!window.confirm(`Excluir ${membro.nome} (${membro.sigla})?${aviso} Esta ação não pode ser desfeita.`)) return
    try {
      await exclusao.mutateAsync(membro.id)
      navegar('/membros')
    } catch (e) {
      setErroAcao(e.message)
    }
  }

  return (
    <section>
      <Link to="/membros" className="voltar">
        ← Membros
      </Link>

      {erroAcao && <p className="alerta alerta--erro">{erroAcao}</p>}

      <header className="perfil">
        <Avatar nome={membro.nome} fotoUrl={membro.foto_url} tamanho={120} />
        <div className="perfil__dados">
          <span className="membro-card__sigla">{membro.sigla}</span>
          <h1>{membro.nome}</h1>
          {membro.cargo && <p className="perfil__cargo">{membro.cargo}</p>}
          <a href={`mailto:${membro.email}`} className="perfil__email">
            {membro.email}
          </a>
        </div>
        <div className="acoes acoes--direita">
          {membro.permissoes.editar && (
            <Link to={`/membros/${membro.id}/editar`} className="botao botao--fantasma">
              Editar
            </Link>
          )}
          {membro.permissoes.excluir && (
            <button type="button" className="botao botao--perigo" onClick={excluirMembro}>
              Excluir
            </button>
          )}
        </div>
      </header>

      <dl className="projeto-infos">
        <div>
          <dt>Projetos</dt>
          <dd>{new Set(alocacoes.map((a) => a.projeto)).size}</dd>
        </div>
        <div>
          <dt>Em andamento</dt>
          <dd>{contar('em_andamento')}</dd>
        </div>
        <div>
          <dt>Planejamento</dt>
          <dd>{contar('planejamento')}</dd>
        </div>
        <div>
          <dt>Concluídos</dt>
          <dd>{contar('concluido')}</dd>
        </div>
      </dl>

      <h2 className="titulo-secao">Projetos</h2>

      {ordenadas.length === 0 ? (
        <Vazio texto="Este membro ainda não está alocado em nenhum projeto." />
      ) : (
        <div className="lista-projetos">
          {ordenadas.map((alocacao) => (
            <Link key={alocacao.id} to={`/projetos/${alocacao.projeto}`} className="projeto-card">
              <div className="projeto-card__topo">
                <h3>{alocacao.projeto_nome}</h3>
                <StatusBadge status={alocacao.projeto_status} texto={alocacao.projeto_status_display} />
              </div>
              <div className="projeto-card__empresa">
                {alocacao.empresa_logo_url && <img src={alocacao.empresa_logo_url} alt="" className="logo-branca" />}
                <span>{alocacao.empresa_nome}</span>
              </div>
              <p className="projeto-card__datas">
                <strong>{alocacao.funcao}</strong> · {alocacao.escopo}
              </p>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
