import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AlocacaoForm from '../components/AlocacaoForm.jsx'
import Avatar from '../components/Avatar.jsx'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import Modal from '../components/Modal.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useApi } from '../hooks/useApi.js'
import { api } from '../services/api.js'
import { formatarData, formatarDuracao } from '../utils/formatar.js'

export default function ProjetoPage() {
  const { id } = useParams()
  const navegar = useNavigate()
  // null = modal fechado; { alocacao: null } = adicionar; { alocacao: {...} } = editar
  const [modal, setModal] = useState(null)
  const [erroAcao, setErroAcao] = useState(null)

  // Projeto, equipe e membros em paralelo; a empresa (para a logo) vem em seguida
  const { dados, carregando, erro, recarregar } = useApi(async () => {
    const [projeto, alocacoes, membros] = await Promise.all([
      api.buscarProjeto(id),
      api.listarAlocacoesDoProjeto(id),
      api.listarMembros(),
    ])
    const empresa = await api.buscarEmpresa(projeto.empresa)
    return { projeto, alocacoes, membros, empresa }
  }, [id])

  if (carregando) return <Carregando />
  if (erro) return <Erro mensagem={erro} />

  const { projeto, alocacoes, membros, empresa } = dados
  const duracao = formatarDuracao(projeto.data_inicio, projeto.data_fim_prevista)

  // Ao adicionar, só aparecem membros que ainda não estão na equipe
  const idsNaEquipe = new Set(alocacoes.map((a) => a.membro))
  const membrosDisponiveis = modal?.alocacao ? membros : membros.filter((m) => !idsNaEquipe.has(m.id))

  async function excluirProjeto() {
    const confirmado = window.confirm(
      `Excluir o projeto ${projeto.nome}? A equipe alocada também será removida. Esta ação não pode ser desfeita.`,
    )
    if (!confirmado) return
    try {
      await api.excluirProjeto(projeto.id)
      navegar(`/projetos/empresa/${empresa.id}`)
    } catch (e) {
      setErroAcao(e.message)
    }
  }

  async function removerDaEquipe(alocacao) {
    if (!window.confirm(`Remover ${alocacao.membro_nome} da equipe do ${projeto.nome}?`)) return
    try {
      await api.excluirAlocacao(alocacao.id)
      recarregar()
    } catch (e) {
      setErroAcao(e.message)
    }
  }

  return (
    <section>
      <Link to={`/projetos/empresa/${empresa.id}`} className="voltar">
        ← Projetos com {empresa.nome}
      </Link>

      {erroAcao && <p className="alerta alerta--erro">{erroAcao}</p>}

      <header className="projeto-cabecalho">
        <div className="projeto-cabecalho__titulo">
          <h1>{projeto.nome}</h1>
          <StatusBadge status={projeto.status} texto={projeto.status_display} />
        </div>

        <div className="acoes">
          <Link to={`/projetos/empresa/${empresa.id}`} className="projeto-cabecalho__empresa">
            {empresa.logo_url && <img src={empresa.logo_url} alt="" className="logo-branca" />}
            <span>{empresa.nome}</span>
          </Link>
          <Link to={`/projetos/${projeto.id}/editar`} className="botao botao--fantasma">
            Editar
          </Link>
          <button type="button" className="botao botao--perigo" onClick={excluirProjeto}>
            Excluir
          </button>
        </div>
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

      <div className="secao-cabecalho">
        <h2 className="titulo-secao">Equipe</h2>
        <button type="button" className="botao botao--primario" onClick={() => setModal({ alocacao: null })}>
          + Adicionar membro
        </button>
      </div>

      {alocacoes.length === 0 ? (
        <Vazio texto="Nenhum membro alocado neste projeto ainda." />
      ) : (
        <div className="grade-equipe">
          {alocacoes.map((alocacao) => (
            <article key={alocacao.id} className="membro-card">
              <div className="membro-card__acoes">
                <button
                  type="button"
                  className="botao botao--icone"
                  onClick={() => setModal({ alocacao })}
                  aria-label={`Editar ${alocacao.membro_nome}`}
                  title="Editar função/escopo"
                >
                  ✎
                </button>
                <button
                  type="button"
                  className="botao botao--icone botao--icone-perigo"
                  onClick={() => removerDaEquipe(alocacao)}
                  aria-label={`Remover ${alocacao.membro_nome}`}
                  title="Remover da equipe"
                >
                  ✕
                </button>
              </div>
              <Avatar nome={alocacao.membro_nome} fotoUrl={alocacao.membro_foto_url} />
              <div className="membro-card__nome">
                <h3>
                  <Link to={`/membros/${alocacao.membro}`} className="link-sutil">
                    {alocacao.membro_nome}
                  </Link>
                </h3>
                <span className="membro-card__sigla">{alocacao.membro_sigla}</span>
              </div>
              <p className="membro-card__funcao">{alocacao.funcao}</p>
              <span className="membro-card__escopo">{alocacao.escopo}</span>
            </article>
          ))}
        </div>
      )}

      <Modal
        aberto={modal !== null}
        titulo={modal?.alocacao ? `Editar ${modal.alocacao.membro_nome}` : `Adicionar membro ao ${projeto.nome}`}
        aoFechar={() => setModal(null)}
      >
        <AlocacaoForm
          projetoId={projeto.id}
          alocacao={modal?.alocacao ?? null}
          membros={membrosDisponiveis}
          aoCancelar={() => setModal(null)}
          aoSalvar={() => {
            setModal(null)
            recarregar()
          }}
        />
      </Modal>
    </section>
  )
}
