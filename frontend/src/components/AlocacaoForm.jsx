import Campo from './Campo.jsx'
import ConsultaAlocacoes from './ConsultaAlocacoes.jsx'
import { useFormulario } from '../hooks/useFormulario.js'
import { useSalvarAlocacao } from '../api/queries.js'

// Mesmas listas do backend (Alocacao.Funcao e Alocacao.Escopo em api/models.py).
const GERENTE = 'Gerente de projeto'
const FUNCOES = [GERENTE, 'Executor']
const ESCOPOS = ['Web', 'Data Science', 'Business Intelligence', 'Visão Computacional', 'AI']

export default function AlocacaoForm({ projetoId, alocacao, alocacoes, membros, idsNaEquipe, aoSalvar, aoCancelar }) {
  const editando = Boolean(alocacao)
  const salvamento = useSalvarAlocacao()
  // Um gerente por projeto: a opção fica bloqueada se outra pessoa já for a gerente.
  const outroGerente = alocacoes.find((a) => a.funcao === GERENTE && a.id !== alocacao?.id)
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
      funcao: valores.funcao,
      escopo: valores.escopo,
    }
    const salva = await enviar(() => salvamento.mutateAsync({ id: editando ? alocacao.id : null, dados: corpo }))
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
        <Campo
          rotulo="Função"
          nome="funcao"
          erro={erros.funcao}
          obrigatorio
          dica={
            outroGerente
              ? `${outroGerente.membro_nome} já é o gerente deste projeto. Mude a função dele para Executor antes.`
              : 'O gerente de projeto edita os dados do projeto e os documentos.'
          }
        >
          <select id="funcao" name="funcao" value={valores.funcao} onChange={alterar}>
            <option value="">Selecione...</option>
            {FUNCOES.map((funcao) => (
              <option key={funcao} value={funcao} disabled={funcao === GERENTE && Boolean(outroGerente)}>
                {funcao}
              </option>
            ))}
          </select>
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
