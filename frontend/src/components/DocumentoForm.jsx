import { useState } from 'react'
import Campo from './Campo.jsx'
import { useFormulario } from '../hooks/useFormulario.js'
import { api } from '../api/useApi.js'
import { formatarTamanho } from '../utils/formatar.js'

const TIPOS_DOCUMENTO = [
  ['abertura', 'Abertura'],
  ['encerramento', 'Encerramento'],
  ['contrato', 'Contrato'],
  ['viabilidade', 'Viabilidade'],
  ['relatorio', 'Relatório'],
  ['ata', 'Ata'],
  ['planejamento', 'Planejamento'],
  ['outro', 'Outro'],
]

const FORMATOS = '.pdf,.doc,.docx,.odt,.txt,.xls,.xlsx,.ods,.csv,.ppt,.pptx,.odp,.png,.jpg,.jpeg,.zip'
const TAMANHO_MAXIMO = 20 * 1024 * 1024

export default function DocumentoForm({ projetoId, aoSalvar, aoCancelar }) {
  const [arquivo, setArquivo] = useState(null)
  const { valores, alterar, erros, erroGeral, enviando, enviar } = useFormulario({
    tipo: 'abertura',
    titulo: '',
  })
  const [erroArquivo, setErroArquivo] = useState(null)

  function escolherArquivo(evento) {
    const escolhido = evento.target.files[0] ?? null
    setErroArquivo(escolhido && escolhido.size > TAMANHO_MAXIMO ? 'O arquivo deve ter no máximo 20 MB.' : null)
    setArquivo(escolhido)
  }

  async function salvar(evento) {
    evento.preventDefault()
    if (!arquivo) {
      setErroArquivo('Escolha um arquivo.')
      return
    }
    if (erroArquivo) return

    const dados = new FormData()
    dados.append('projeto', projetoId)
    dados.append('tipo', valores.tipo)
    dados.append('titulo', valores.titulo.trim())
    dados.append('arquivo', arquivo)

    const salvo = await enviar(() => api.enviarDocumento(dados))
    if (salvo) aoSalvar()
  }

  const mensagemArquivo = erroArquivo ?? (erros.arquivo && [].concat(erros.arquivo).join(' '))

  return (
    <form className="formulario" onSubmit={salvar} noValidate>
      {erroGeral && !erros.arquivo && <p className="alerta alerta--erro">{erroGeral}</p>}

      <div className={`campo ${mensagemArquivo ? 'campo--erro' : ''}`}>
        <span className="campo__rotulo">
          Arquivo<span className="campo__obrigatorio"> *</span>
        </span>
        <label className={`upload ${arquivo ? 'upload--escolhido' : ''}`}>
          <input type="file" accept={FORMATOS} onChange={escolherArquivo} className="upload__input" />
          {arquivo ? (
            <>
              <strong className="upload__nome">{arquivo.name}</strong>
              <span>{formatarTamanho(arquivo.size)} · clique para trocar</span>
            </>
          ) : (
            <>
              <strong>Clique para escolher um arquivo</strong>
              <span>PDF, Word, Excel, PowerPoint, imagem ou ZIP · até 20 MB</span>
            </>
          )}
        </label>
        {mensagemArquivo && <p className="campo__mensagem">{mensagemArquivo}</p>}
      </div>

      <div className="formulario__linha">
        <Campo rotulo="Tipo" nome="tipo" erro={erros.tipo} obrigatorio>
          <select id="tipo" name="tipo" value={valores.tipo} onChange={alterar}>
            {TIPOS_DOCUMENTO.map(([valor, texto]) => (
              <option key={valor} value={valor}>
                {texto}
              </option>
            ))}
          </select>
        </Campo>
        <Campo rotulo="Título" nome="titulo" erro={erros.titulo} dica="Se ficar vazio, usa o nome do arquivo.">
          <input id="titulo" name="titulo" value={valores.titulo} maxLength={150} onChange={alterar} />
        </Campo>
      </div>

      <div className="formulario__acoes">
        <button type="button" className="botao botao--fantasma" onClick={aoCancelar}>
          Cancelar
        </button>
        <button type="submit" className="botao botao--primario" disabled={enviando}>
          {enviando ? 'Enviando...' : 'Enviar documento'}
        </button>
      </div>
    </form>
  )
}
