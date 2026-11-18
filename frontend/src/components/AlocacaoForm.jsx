import Campo from './Campo.jsx'
import ConsultaAlocacoes from './ConsultaAlocacoes.jsx'
import { useFormulario } from '../hooks/useFormulario.js'
import { api } from '../api/useApi.js'

const FUNCOES = ['Gerente de projeto', 'Executor']
const ESCOPOS = ['Web', 'Data Science', 'Business Intelligence', 'Visão Computacional', 'AI']

export default function AlocacaoForm({ projetoId, alocacao, membros, idsNaEquipe, aoSalvar, aoCancelar }) {
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
      escopo: valores.escopo,
    }
    const salva = await enviar(() =>
      editando ? api.atualizarAlocacao(alocacao.id, corpo) : api.criarAlocacao(corpo),
    )
    if (salva) aoSalvar()
  }

  return (
    <form className="formulario" onSubmit={salvar} noValidate>
      {erroGeral && <p className="alerta alerta--erro">{erroGeral}</p>}

      {editando ? (
        <Campo rotulo="Membro" nome="membro">
          <select id="membro" name="membro" value={valores.membro} disabled>
            {membros.map((membro) => (
              <option key={membro.id} value={membro.id}>
                {membro.sigla} · {membro.nome}
              </option>
            ))}
          </select>
        </Campo>
      ) : (
        <div className={`campo ${erros.membro ? 'campo--erro' : ''}`}>
          <span className="campo__rotulo">
            Membro<span className="campo__obrigatorio"> *</span>
          </span>
          <ConsultaAlocacoes
            membros={membros}
            idsNaEquipe={idsNaEquipe}
            selecionado={valores.membro}
            aoSelecionar={(id) => alterar({ target: { name: 'membro', value: id } })}
          />
          {erros.membro && <p className="campo__mensagem">{[].concat(erros.membro).join(' ')}</p>}
        </div>
      )}

      <div className="formulario__linha">
        <Campo rotulo="Função" nome="funcao" erro={erros.funcao} obrigatorio>
          <input id="funcao" name="funcao" list="lista-funcoes" value={valores.funcao} maxLength={60} onChange={alterar} />
        </Campo>
        <Campo rotulo="Escopo" nome="escopo" erro={erros.escopo} obrigatorio>
          <select id="escopo" name="escopo" value={valores.escopo} onChange={alterar}>
            <option value="">Selecione...</option>
            {ESCOPOS.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </Campo>
      </div>

      <datalist id="lista-funcoes">
        {FUNCOES.map((f) => (
          <option key={f} value={f} />
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
