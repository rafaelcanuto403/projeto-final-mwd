import { Link, useNavigate, useParams } from 'react-router-dom'
import Avatar from '../components/Avatar.jsx'
import Campo from '../components/Campo.jsx'
import { Carregando, Erro } from '../components/Estado.jsx'
import { useQueryClient } from '@tanstack/react-query'
import { consultas, useConsultas, useSalvarMembro } from '../api/queries.js'
import { NOMES_DOS_PAPEIS, useAuth } from '../auth/useAuth.js'
import { SemPermissao } from '../auth/Rotas.jsx'
import { useFormulario } from '../hooks/useFormulario.js'

const NOVO_MEMBRO = { sigla: '', nome: '', email: '', foto_url: '', cargo: '' }
const CARGO_ADMIN = 'AG PRJ'
// Regra interna do NEO: cada cargo tem um único ocupante por semestre, exceto estes.
const CARGOS_REPETIVEIS = ['executor pleno', 'calouro']

const normalizarCargo = (cargo) => (cargo ?? '').trim().split(/\s+/).join(' ').toLowerCase()
const ehCargoAdmin = (cargo) => normalizarCargo(cargo) === CARGO_ADMIN.toLowerCase()
const ehCargoUnico = (cargo) => Boolean(normalizarCargo(cargo)) && !CARGOS_REPETIVEIS.includes(normalizarCargo(cargo))

export default function MembroFormPage() {
  const { id } = useParams()
  const editando = Boolean(id)
  const { dados, carregando, erro } = useConsultas(
    editando ? [consultas.membro(id), consultas.membros()] : [consultas.membros()],
  )

  if (carregando) return <Carregando />
  if (erro) return <Erro mensagem={erro} />

  const [membro, membros] = editando ? dados : [null, ...dados]
  if (membro && !membro.permissoes.editar) return <SemPermissao />

  return <MembroForm inicial={membro ?? NOVO_MEMBRO} membros={membros} editando={editando} />
}

function MembroForm({ inicial, membros, editando }) {
  const navegar = useNavigate()
  const { usuario, recarregarUsuario } = useAuth()
  const queryClient = useQueryClient()
  const salvamento = useSalvarMembro()
  const souAdmin = usuario.papel === 'admin'
  const proprioPerfil = editando && usuario.membro?.id === inicial.id
  // ABAC: quem não é Admin só altera nome, foto e senha do próprio perfil.
  const restrito = !souAdmin

  const { valores, alterar, erros, erroGeral, enviando, enviar } = useFormulario({
    sigla: inicial.sigla,
    nome: inicial.nome,
    email: inicial.email,
    foto_url: inicial.foto_url ?? '',
    cargo: inicial.cargo ?? '',
    senha: '',
  })
  const cargoAdmin = ehCargoAdmin(valores.cargo)
  // Quem ocupa hoje o cargo digitado: ao salvar, o cargo passa para este membro.
  const ocupante =
    !restrito && ehCargoUnico(valores.cargo)
      ? membros.find((m) => m.id !== inicial.id && normalizarCargo(m.cargo) === normalizarCargo(valores.cargo))
      : null
  const voltarPara = editando ? `/membros/${inicial.id}` : '/membros'

  async function salvar(evento) {
    evento.preventDefault()
    const quem = valores.nome.trim() || 'este membro'
    // Passar o AG PRJ é passar o papel de Admin (o ocupante é o próprio Admin logado).
    const passaAdmin = Boolean(ocupante) && cargoAdmin
    const aviso = passaAdmin
      ? `Só um membro pode ser ${CARGO_ADMIN}. Ao salvar, ${quem} passa a ser ${CARGO_ADMIN} e Admin, ` +
        'e você deixa o cargo e o papel de Admin. Continuar?'
      : `O cargo ${valores.cargo.trim()} hoje é de ${ocupante?.nome} (${ocupante?.sigla}). ` +
        `Ao salvar, ele passa para ${quem} e ${ocupante?.nome} fica sem cargo. Continuar?`
    if (ocupante && !window.confirm(aviso)) return

    const corpo = { nome: valores.nome.trim(), foto_url: valores.foto_url.trim() || null }
    if (!restrito) {
      Object.assign(corpo, {
        sigla: valores.sigla,
        email: valores.email,
        cargo: valores.cargo.trim(),
      })
    }
    if (valores.senha) corpo.senha = valores.senha

    const salvo = await enviar(() => salvamento.mutateAsync({ id: editando ? inicial.id : null, dados: corpo }))
    if (!salvo) return
    if (proprioPerfil || passaAdmin) await recarregarUsuario()
    // Quem passou o AG PRJ deixou de ser Admin: as permissões em cache (botões de cada projeto,
    // documento...) foram calculadas para o papel antigo, então tudo é buscado de novo.
    if (passaAdmin) await queryClient.invalidateQueries()
    navegar(`/membros/${salvo.id}`)
  }

  const titulo = !editando ? 'Novo membro' : proprioPerfil ? 'Editar meu perfil' : `Editar ${inicial.nome}`

  return (
    <section className="formulario-pagina">
      <Link to={voltarPara} className="voltar">
        ← Voltar
      </Link>
      <h1>{titulo}</h1>

      <form className="formulario" onSubmit={salvar} noValidate>
        {erroGeral && <p className="alerta alerta--erro">{erroGeral}</p>}
        {restrito && (
          <p className="alerta alerta--info">
            Sigla, e-mail e cargo só podem ser alterados por um Admin.
          </p>
        )}

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
              disabled={restrito}
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
          <Campo rotulo="E-mail" nome="email" erro={erros.email} obrigatorio dica="Também é o login do membro.">
            <input
              id="email"
              name="email"
              type="email"
              value={valores.email}
              maxLength={160}
              disabled={restrito}
              onChange={alterar}
            />
          </Campo>
          <Campo
            rotulo="Cargo"
            nome="cargo"
            erro={erros.cargo}
            dica={
              proprioPerfil && souAdmin
                ? `Como ${CARGO_ADMIN}, você só deixa este cargo passando-o ao seu sucessor.`
                : ocupante
                  ? `Hoje é de ${ocupante.nome} (${ocupante.sigla}). Ao salvar, o cargo passa para este membro.`
                  : `Cada cargo é de um só membro (exceto Executor Pleno e Calouro). ${CARGO_ADMIN} é o Admin.`
            }
          >
            <input
              id="cargo"
              name="cargo"
              value={valores.cargo}
              maxLength={80}
              placeholder="Ex.: Executor Pleno"
              disabled={restrito}
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

        <div className="formulario__linha">
          <Campo
            rotulo="Papel"
            nome="papel"
            dica={`Definido pelo cargo: ${CARGO_ADMIN} é Admin; os demais são Membros. Quem gerencia cada projeto é escolhido na equipe do projeto.`}
          >
            <input id="papel" value={NOMES_DOS_PAPEIS[cargoAdmin ? 'admin' : 'membro']} disabled readOnly />
          </Campo>
          <Campo
            rotulo={editando ? 'Nova senha' : 'Senha inicial'}
            nome="senha"
            erro={erros.senha}
            dica={
              editando
                ? 'Deixe em branco para manter a senha atual.'
                : 'Se ficar vazia, o membro é cadastrado sem acesso ao sistema.'
            }
          >
            <input
              id="senha"
              name="senha"
              type="password"
              autoComplete="new-password"
              value={valores.senha}
              onChange={alterar}
            />
          </Campo>
        </div>

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
