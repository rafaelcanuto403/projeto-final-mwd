import Avatar from './Avatar.jsx'
import { Carregando, Erro } from './Estado.jsx'
import { useQuery } from '@tanstack/react-query'
import { consultas } from '../api/queries.js'

function contarPorMembro(alocacoes, status) {
  const projetosPorMembro = new Map()
  for (const alocacao of alocacoes) {
    if (alocacao.projeto_status !== status) continue
    const projetos = projetosPorMembro.get(alocacao.membro) ?? new Set()
    projetos.add(alocacao.projeto)
    projetosPorMembro.set(alocacao.membro, projetos)
  }
  return (membroId) => projetosPorMembro.get(membroId)?.size ?? 0
}

export default function ConsultaAlocacoes({ membros, idsNaEquipe, selecionado, aoSelecionar }) {
  const { data: alocacoes, isPending: carregando, error } = useQuery(consultas.alocacoes())
  const erro = error?.message

  if (carregando) return <Carregando />
  if (erro) return <Erro mensagem={erro} />

  const emAndamento = contarPorMembro(alocacoes, 'em_andamento')
  const ordenados = [...membros].sort(
    (a, b) =>
      idsNaEquipe.has(a.id) - idsNaEquipe.has(b.id) ||
      emAndamento(a.id) - emAndamento(b.id) ||
      a.nome.localeCompare(b.nome, 'pt-BR'),
  )

  return (
    <ul className="consulta" role="radiogroup" aria-label="Membro">
      {ordenados.map((membro) => {
        const atuais = emAndamento(membro.id)
        const naEquipe = idsNaEquipe.has(membro.id)
        const escolhido = selecionado === String(membro.id)
        return (
          <li key={membro.id}>
            <label
              className={[
                'consulta__item',
                escolhido && 'consulta__item--escolhido',
                naEquipe && 'consulta__item--bloqueado',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              <input
                type="radio"
                name="membro"
                value={membro.id}
                checked={escolhido}
                disabled={naEquipe}
                onChange={() => aoSelecionar(String(membro.id))}
                className="consulta__radio"
              />
              <Avatar nome={membro.nome} fotoUrl={membro.foto_url} tamanho={36} />
              <div className="consulta__nome">
                <strong>{membro.nome}</strong>
                <span>
                  {membro.sigla}
                  {membro.cargo && ` · ${membro.cargo}`}
                  {naEquipe && <em className="consulta__na-equipe">já na equipe</em>}
                </span>
              </div>
              <div className="consulta__numero">
                <strong className={atuais === 0 ? 'consulta__numero--zero' : undefined}>{atuais}</strong>
                <span>{atuais === 1 ? 'projeto' : 'projetos'}</span>
              </div>
            </label>
          </li>
        )
      })}
    </ul>
  )
}
