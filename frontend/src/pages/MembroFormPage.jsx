import { Link, useNavigate, useParams } from 'react-router-dom'
import Avatar from '../components/Avatar.jsx'
import Campo from '../components/Campo.jsx'
import { Carregando, Erro } from '../components/Estado.jsx'
import { api, useApi } from '../api/useApi.js'
import { useFormulario } from '../hooks/useFormulario.js'

export default function MembroFormPage() {
  const { id } = useParams()
  const editando = Boolean(id)
  const { dados, carregando, erro } = useApi(
    () => (editando ? api.buscarMembro(id) : Promise.resolve(null)),
    [id],
  )

  if (carregando) return <Carregando />
  if (erro) return <Erro mensagem={erro} />

  return <MembroForm inicial={dados ?? { sigla: '', nome: '', email: '', foto_url: '', cargo: '' }} editando={editando} />
}

function MembroForm({ inicial, editando }) {
  const navegar = useNavigate()
  const { valores, alterar, erros, erroGeral, enviando, enviar } = useFormulario({
    sigla: inicial.sigla,
    nome: inicial.nome,
    email: inicial.email,
    foto_url: inicial.foto_url ?? '',
    cargo: inicial.cargo ?? '',
  })
  const voltarPara = editando ? `/membros/${inicial.id}` : '/membros'

  async function salvar(evento) {
    evento.preventDefault()
    const corpo = {
      sigla: valores.sigla,
      nome: valores.nome.trim(),
      email: valores.email,
      foto_url: valores.foto_url.trim() || null,
      cargo: valores.cargo.trim(),
    }
    const salvo = await enviar(() =>
      editando ? api.atualizarMembro(inicial.id, corpo) : api.criarMembro(corpo),
    )
    if (salvo) navegar(`/membros/${salvo.id}`)
  }

  return (
    <section className="formulario-pagina">
      <Link to={voltarPara} className="voltar">
        ← Voltar
      </Link>
      <h1>{editando ? `Editar ${inicial.nome}` : 'Novo membro'}</h1>

      <form className="formulario" onSubmit={salvar} noValidate>
        {erroGeral && <p className="alerta alerta--erro">{erroGeral}</p>}

        <div className="formulario__previa-membro">
          <Avatar key={valores.foto_url} nome={valores.nome || '?'} fotoUrl={valores.foto_url.trim()} tamanho={96} />
          <div>
            <span className="membro-card__sigla">{valores.sigla.toUpperCase() || 'SIG'}</span>
            <p className="formulario__previa-nome">{valores.nome || 'Nome do membro'}</p>
          </div>
        </div>

        <div className="formulario__linha formulario__linha--sigla">
          <Campo rotulo="Sigla" nome="sigla" erro={erros.sigla} obrigatorio dica="3 letras">
            <input
              id="sigla"
              name="sigla"
              value={valores.sigla}
              maxLength={3}
              autoComplete="off"
              className="campo__sigla"
              onChange={(e) =>
                alterar({ target: { name: 'sigla', value: e.target.value.toUpperCase().replace(/[^A-Z]/g, '') } })
              }
            />
          </Campo>
          <Campo rotulo="Nome" nome="nome" erro={erros.nome} obrigatorio>
            <input id="nome" name="nome" value={valores.nome} maxLength={120} onChange={alterar} />
          </Campo>
        </div>

        <div className="formulario__linha">
          <Campo rotulo="E-mail" nome="email" erro={erros.email} obrigatorio>
            <input id="email" name="email" type="email" value={valores.email} maxLength={160} onChange={alterar} />
          </Campo>
          <Campo rotulo="Cargo" nome="cargo" erro={erros.cargo}>
            <input
              id="cargo"
              name="cargo"
              value={valores.cargo}
              maxLength={80}
              placeholder="Ex.: Executor Pleno"
              onChange={alterar}
            />
          </Campo>
        </div>

        <Campo
          rotulo="Foto"
          nome="foto_url"
          erro={erros.foto_url}
          dica="Link da imagem. Se a foto estiver no Google Drive, o arquivo precisa estar compartilhado com 'Qualquer pessoa com o link'."
        >
          <input
            id="foto_url"
            name="foto_url"
            value={valores.foto_url}
            maxLength={500}
            placeholder="https://..."
            onChange={alterar}
          />
        </Campo>

        <div className="formulario__acoes">
          <Link to={voltarPara} className="botao botao--fantasma">
            Cancelar
          </Link>
          <button type="submit" className="botao botao--primario" disabled={enviando}>
            {enviando ? 'Salvando...' : editando ? 'Salvar alterações' : 'Criar membro'}
          </button>
        </div>
      </form>
    </section>
  )
}
