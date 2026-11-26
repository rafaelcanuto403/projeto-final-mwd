import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AlocacaoForm from '../components/AlocacaoForm.jsx'
import Avatar from '../components/Avatar.jsx'
import DescricaoProjeto from '../components/DescricaoProjeto.jsx'
import DocumentoCard from '../components/DocumentoCard.jsx'
import DocumentoForm from '../components/DocumentoForm.jsx'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import Modal from '../components/Modal.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import VisualizadorDocumento from '../components/VisualizadorDocumento.jsx'
import {
  consultas,
  useBaixarDocumento,
  useConsultas,
  useExcluirAlocacao,
  useExcluirDocumento,
  useExcluirProjeto,
} from '../api/queries.js'
import { formatarData, formatarDuracao } from '../utils/formatar.js'

const MAX_MEMBROS = 3

export default function ProjetoPage() {
  const { id } = useParams()
  const navegar = useNavigate()
  const [modal, setModal] = useState(null)
  const [erroAcao, setErroAcao] = useState(null)
  const [enviandoDocumento, setEnviandoDocumento] = useState(false)
  const [visualizando, setVisualizando] = useState(null)
  const exclusaoDoProjeto = useExcluirProjeto()
  const exclusaoDeDocumento = useExcluirDocumento()
  const exclusaoDeAlocacao = useExcluirAlocacao()
  const baixar = useBaixarDocumento()

  // As quatro buscas saem em paralelo; cada uma tem seu cache (voltar a esta página é instantâneo).
  const { dados, carregando, erro } = useConsultas([
    consultas.projeto(id),
    consultas.alocacoesDoProjeto(id),
    consultas.membros(),
    consultas.documentosDoProjeto(id),
  ])

  if (carregando) return <Carregando />
  if (erro) return <Erro mensagem={erro} />

  const [projeto, alocacoes, membros, documentos] = dados
  // O projeto já traz nome e logo da empresa: não precisa de outra requisição.
  const empresa = { id: projeto.empresa, nome: projeto.empresa_nome, logo_url: projeto.empresa_logo_url }
  const pode = projeto.permissoes
  const somenteLeitura = projeto.status === 'concluido' && !pode.editar
  const duracao = formatarDuracao(projeto.data_inicio, projeto.data_fim_prevista)

  const equipeCompleta = alocacoes.length >= MAX_MEMBROS
  const idsNaEquipe = new Set(alocacoes.map((a) => a.membro))

  async function excluirProjeto() {
    const confirmado = window.confirm(
      `Excluir o projeto ${projeto.nome}? A equipe alocada também será removida. Esta ação não pode ser desfeita.`,
    )
    if (!confirmado) return
    try {
      await exclusaoDoProjeto.mutateAsync(projeto.id)
      navegar(`/projetos/empresa/${empresa.id}`)
    } catch (e) {
      setErroAcao(e.message)
    }
  }

  async function baixarDocumento(documento) {
    try {
      await baixar(documento)
    } catch (e) {
      setErroAcao(e.message)
    }
  }

  async function excluirDocumento(documento) {
    if (!window.confirm(`Excluir o documento "${documento.titulo}"? O arquivo será apagado.`)) return
    try {
      await exclusaoDeDocumento.mutateAsync(documento.id)
    } catch (e) {
      setErroAcao(e.message)
    }
  }

  async function removerDaEquipe(alocacao) {
    if (!window.confirm(`Remover ${alocacao.membro_nome} da equipe do ${projeto.nome}?`)) return
    try {
      await exclusaoDeAlocacao.mutateAsync(alocacao.id)
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
          {pode.editar && (
            <Link to={`/projetos/${projeto.id}/editar`} className="botao botao--fantasma">
              Editar
            </Link>
          )}
          {pode.excluir && (
            <button type="button" className="botao botao--perigo" onClick={excluirProjeto}>
              Excluir
            </button>
          )}
        </div>
      </header>

      <DescricaoProjeto descricao={projeto.descricao} className="projeto-descricao" />

      {somenteLeitura && (
        <p className="alerta alerta--info">Projeto concluído: somente AG PRJ pode alterá-lo.</p>
      )}

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
        <div className="acoes">
          {pode.enviar_documento && (
            <button type="button" className="botao botao--fantasma" onClick={() => setEnviandoDocumento(true)}>
              + Adicionar documento
            </button>
          )}
          {pode.gerenciar_equipe && (
            <button
              type="button"
              className="botao botao--primario"
              onClick={() => setModal({ alocacao: null })}
              disabled={equipeCompleta}
              title={equipeCompleta ? `A equipe já tem ${MAX_MEMBROS} membros, o máximo por projeto` : undefined}
            >
              + Adicionar membro
            </button>
          )}
        </div>
      </div>

      {alocacoes.length === 0 ? (
        <Vazio texto="Nenhum membro alocado neste projeto ainda." />
      ) : (
        <div className="grade-equipe">
          {alocacoes.map((alocacao) => (
            <article key={alocacao.id} className="membro-card">
              {pode.gerenciar_equipe && (
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
              )}
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

      <h2 className="titulo-secao secao-documentos">Documentos</h2>
      {!pode.ver_documentos ? (
        <Vazio texto="Os documentos ficam visíveis apenas para a equipe do projeto e o Admin." />
      ) : documentos.length === 0 ? (
        <Vazio texto="Nenhum documento enviado." />
      ) : (
        <ul className="grade-documentos">
          {documentos.map((documento) => (
            <DocumentoCard
              key={documento.id}
              documento={documento}
              aoAbrir={() => setVisualizando(documento)}
              aoBaixar={() => baixarDocumento(documento)}
              aoExcluir={() => excluirDocumento(documento)}
            />
          ))}
        </ul>
      )}

      <Modal
        aberto={visualizando !== null}
        titulo={visualizando?.titulo}
        aoFechar={() => setVisualizando(null)}
        largo
      >
        <VisualizadorDocumento documento={visualizando} />
      </Modal>

      <Modal
        aberto={enviandoDocumento}
        titulo={`Adicionar documento ao ${projeto.nome}`}
        aoFechar={() => setEnviandoDocumento(false)}
      >
        <DocumentoForm
          projetoId={projeto.id}
          podeContrato={pode.enviar_contrato}
          aoCancelar={() => setEnviandoDocumento(false)}
          aoSalvar={() => setEnviandoDocumento(false)}
        />
      </Modal>

      <Modal
        aberto={modal !== null}
        titulo={modal?.alocacao ? `Editar ${modal.alocacao.membro_nome}` : `Adicionar membro ao ${projeto.nome}`}
        aoFechar={() => setModal(null)}
      >
        <AlocacaoForm
          projetoId={projeto.id}
          alocacao={modal?.alocacao ?? null}
          alocacoes={alocacoes}
          membros={membros}
          idsNaEquipe={idsNaEquipe}
          aoCancelar={() => setModal(null)}
          aoSalvar={() => setModal(null)}
        />
      </Modal>
    </section>
  )
}
