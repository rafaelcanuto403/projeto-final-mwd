import { Link, useNavigate, useParams } from 'react-router-dom'
import Campo from '../components/Campo.jsx'
import { Carregando, Erro } from '../components/Estado.jsx'
import { useApi } from '../hooks/useApi.js'
import { useFormulario } from '../hooks/useFormulario.js'
import { api } from '../services/api.js'

// Página usada para criar (/projetos/empresa/nova) e editar (/projetos/empresa/:id/editar)
export default function EmpresaFormPage() {
  const { id } = useParams()
  const editando = Boolean(id)
  const { dados, carregando, erro } = useApi(
    () => (editando ? api.buscarEmpresa(id) : Promise.resolve(null)),
    [id],
  )

  if (carregando) return <Carregando />
  if (erro) return <Erro mensagem={erro} />

  return <EmpresaForm inicial={dados ?? { nome: '', logo_url: '' }} editando={editando} />
}

function EmpresaForm({ inicial, editando }) {
  const navegar = useNavigate()
  const { valores, alterar, erros, erroGeral, enviando, enviar } = useFormulario({
    nome: inicial.nome,
    logo_url: inicial.logo_url ?? '',
  })
  const voltarPara = editando ? `/projetos/empresa/${inicial.id}` : '/projetos'

  async function salvar(evento) {
    evento.preventDefault()
    const corpo = { nome: valores.nome.trim(), logo_url: valores.logo_url.trim() || null }
    const salva = await enviar(() =>
      editando ? api.atualizarEmpresa(inicial.id, corpo) : api.criarEmpresa(corpo),
    )
    if (salva) navegar(`/projetos/empresa/${salva.id}`)
  }

  return (
    <section className="formulario-pagina">
      <Link to={voltarPara} className="voltar">
        ← Voltar
      </Link>
      <h1>{editando ? `Editar ${inicial.nome}` : 'Nova empresa parceira'}</h1>

      <form className="formulario" onSubmit={salvar} noValidate>
        {erroGeral && <p className="alerta alerta--erro">{erroGeral}</p>}

        <Campo rotulo="Nome" nome="nome" erro={erros.nome} obrigatorio>
          <input id="nome" name="nome" value={valores.nome} maxLength={100} onChange={alterar} required />
        </Campo>

        <Campo
          rotulo="Logo"
          nome="logo_url"
          erro={erros.logo_url}
          dica="Caminho de um arquivo em frontend/public/logos (ex.: /logos/weg.svg) ou um link https://. Use SVG/PNG com fundo transparente."
        >
          <input
            id="logo_url"
            name="logo_url"
            value={valores.logo_url}
            maxLength={500}
            placeholder="/logos/nome-da-empresa.svg"
            onChange={alterar}
          />
        </Campo>

        <div className="previa-logo" aria-label="Prévia do card">
          <span className="previa-logo__rotulo">Prévia</span>
          <div className="empresa-card empresa-card--previa">
            <div className="empresa-card__logo">
              {valores.logo_url ? (
                <img src={valores.logo_url} alt="" className="logo-branca" />
              ) : (
                <span className="empresa-card__nome">{valores.nome || 'Nome da empresa'}</span>
              )}
            </div>
            <span className="empresa-card__total">
              {inicial.total_projetos ?? 0} {inicial.total_projetos === 1 ? 'projeto' : 'projetos'}
            </span>
          </div>
        </div>

        <div className="formulario__acoes">
          <Link to={voltarPara} className="botao botao--fantasma">
            Cancelar
          </Link>
          <button type="submit" className="botao botao--primario" disabled={enviando}>
            {enviando ? 'Salvando...' : editando ? 'Salvar alterações' : 'Criar empresa'}
          </button>
        </div>
      </form>
    </section>
  )
}
