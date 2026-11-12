import Campo from './Campo.jsx'
import { useFormulario } from '../hooks/useFormulario.js'
import { api } from '../services/api.js'

const FUNCOES = ['Gerente de projeto', 'Executor', 'Consultor', 'Trainee']
const ESCOPOS = ['Gestão', 'Software', 'Hardware', 'Dados', 'Processos', 'Design', 'Pesquisa']

// Formulário (usado dentro do Modal) para adicionar ou editar um membro na equipe.
// - alocacao: a alocação sendo editada, ou null para adicionar
// - membros: membros que podem ser escolhidos
export default function AlocacaoForm({ projetoId, alocacao, membros, aoSalvar, aoCancelar }) {
  const editando = Boolean(alocacao)
  const { valores, alterar, erros, erroGeral, enviando, enviar } = useFormulario({
    membro: alocacao ? String(alocacao.membro) : '',
    funcao: alocacao?.funcao ?? '',
    escopo: alocacao?.escopo ?? '',
  })

  async function salvar(evento) {
    evento.preventDefault()
    const corpo = {
      membro: Number(valores.membro) || null,
      projeto: projetoId,
      funcao: valores.funcao.trim(),
      escopo: valores.escopo.trim(),
    }
    const salva = await enviar(() =>
      editando ? api.atualizarAlocacao(alocacao.id, corpo) : api.criarAlocacao(corpo),
    )
    if (salva) aoSalvar()
  }

  return (
    <form className="formulario" onSubmit={salvar} noValidate>
      {erroGeral && <p className="alerta alerta--erro">{erroGeral}</p>}

      <Campo rotulo="Membro" nome="membro" erro={erros.membro} obrigatorio>
        <select
          id="membro"
          name="membro"
          value={valores.membro}
          onChange={alterar}
          disabled={editando} // ao editar, só função e escopo mudam
        >
          <option value="">Selecione...</option>
          {membros.map((membro) => (
            <option key={membro.id} value={membro.id}>
              {membro.sigla} · {membro.nome}
            </option>
          ))}
        </select>
      </Campo>

      <div className="formulario__linha">
        <Campo rotulo="Função" nome="funcao" erro={erros.funcao} obrigatorio>
          <input id="funcao" name="funcao" list="lista-funcoes" value={valores.funcao} maxLength={60} onChange={alterar} />
        </Campo>
        <Campo rotulo="Escopo" nome="escopo" erro={erros.escopo} obrigatorio>
          <input id="escopo" name="escopo" list="lista-escopos" value={valores.escopo} maxLength={60} onChange={alterar} />
        </Campo>
      </div>

      {/* Sugestões nos campos de texto (o usuário ainda pode digitar outro valor) */}
      <datalist id="lista-funcoes">
        {FUNCOES.map((f) => (
          <option key={f} value={f} />
        ))}
      </datalist>
      <datalist id="lista-escopos">
        {ESCOPOS.map((e) => (
          <option key={e} value={e} />
        ))}
      </datalist>

      <div className="formulario__acoes">
        <button type="button" className="botao botao--fantasma" onClick={aoCancelar}>
          Cancelar
        </button>
        <button type="submit" className="botao botao--primario" disabled={enviando}>
          {enviando ? 'Salvando...' : editando ? 'Salvar' : 'Adicionar à equipe'}
        </button>
      </div>
    </form>
  )
}
