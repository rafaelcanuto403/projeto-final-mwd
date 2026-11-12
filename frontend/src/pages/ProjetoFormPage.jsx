import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import Campo from '../components/Campo.jsx'
import { Carregando, Erro } from '../components/Estado.jsx'
import { useApi } from '../hooks/useApi.js'
import { useFormulario } from '../hooks/useFormulario.js'
import { api } from '../services/api.js'

const STATUS = [
  ['planejamento', 'Planejamento'],
  ['em_andamento', 'Em andamento'],
  ['concluido', 'Concluído'],
]

// Próximo código da EP: inicial + (maior número já usado + 1). Ex.: C157 → C158
async function sugerirNome(empresa) {
  const projetos = await api.listarProjetosDaEmpresa(empresa.id)
  const inicial = empresa.nome[0].toUpperCase()
  const numeros = projetos
    .map((p) => p.nome.match(new RegExp(`^${inicial}(\\d+)$`, 'i'))?.[1])
    .filter(Boolean)
    .map(Number)
  return `${inicial}${numeros.length ? Math.max(...numeros) + 1 : 1}`
}

// Valores iniciais de um projeto novo (início = hoje, no fuso local)
function valoresDeNovoProjeto(empresaId) {
  const hoje = new Date()
  const doisDigitos = (n) => String(n).padStart(2, '0')
  return {
    nome: '',
    descricao: '',
    empresa: empresaId ?? '',
    status: 'planejamento',
    data_inicio: `${hoje.getFullYear()}-${doisDigitos(hoje.getMonth() + 1)}-${doisDigitos(hoje.getDate())}`,
    data_fim_prevista: '',
  }
}

// Página usada para criar (/projetos/novo?empresa=ID) e editar (/projetos/:id/editar)
export default function ProjetoFormPage() {
  const { id } = useParams()
  const [busca] = useSearchParams()
  const editando = Boolean(id)

  const { dados, carregando, erro } = useApi(
    () => Promise.all([api.listarEmpresas(), editando ? api.buscarProjeto(id) : null]),
    [id],
  )

  if (carregando) return <Carregando />
  if (erro) return <Erro mensagem={erro} />

  const [empresas, projeto] = dados
  const inicial = projeto ?? valoresDeNovoProjeto(busca.get('empresa'))

  return <ProjetoForm empresas={empresas} inicial={inicial} editando={editando} />
}

function ProjetoForm({ empresas, inicial, editando }) {
  const navegar = useNavigate()
  const { valores, setValores, alterar, erros, erroGeral, enviando, enviar } = useFormulario({
    ...inicial,
    empresa: String(inicial.empresa ?? ''),
    descricao: inicial.descricao ?? '',
    data_fim_prevista: inicial.data_fim_prevista ?? '',
  })
  // Enquanto o usuário não digitar um nome próprio, o nome acompanha a EP escolhida
  const [nomeAutomatico, setNomeAutomatico] = useState(!editando)

  useEffect(() => {
    if (!nomeAutomatico || !valores.empresa) return
    const empresa = empresas.find((e) => String(e.id) === valores.empresa)
    if (!empresa) return
    let ativo = true
    sugerirNome(empresa).then((nome) => ativo && setValores((v) => ({ ...v, nome })))
    return () => {
      ativo = false
    }
  }, [valores.empresa, nomeAutomatico, empresas, setValores])

  const voltarPara = editando
    ? `/projetos/${inicial.id}`
    : valores.empresa
      ? `/projetos/empresa/${valores.empresa}`
      : '/projetos'

  async function salvar(evento) {
    evento.preventDefault()
    const corpo = {
      ...valores,
      empresa: Number(valores.empresa) || null,
      descricao: valores.descricao.trim() || null,
      data_fim_prevista: valores.data_fim_prevista || null,
    }
    const salvo = await enviar(() =>
      editando ? api.atualizarProjeto(inicial.id, corpo) : api.criarProjeto(corpo),
    )
    if (salvo) navegar(`/projetos/${salvo.id}`)
  }

  return (
    <section className="formulario-pagina">
      <Link to={voltarPara} className="voltar">
        ← Voltar
      </Link>
      <h1>{editando ? `Editar ${inicial.nome}` : 'Novo projeto'}</h1>

      <form className="formulario" onSubmit={salvar} noValidate>
        {erroGeral && <p className="alerta alerta--erro">{erroGeral}</p>}

        <div className="formulario__linha">
          <Campo rotulo="Empresa parceira" nome="empresa" erro={erros.empresa} obrigatorio>
            <select id="empresa" name="empresa" value={valores.empresa} onChange={alterar} required>
              <option value="">Selecione...</option>
              {empresas.map((empresa) => (
                <option key={empresa.id} value={empresa.id}>
                  {empresa.nome}
                </option>
              ))}
            </select>
          </Campo>

          <Campo
            rotulo="Nome"
            nome="nome"
            erro={erros.nome}
            obrigatorio
            dica={nomeAutomatico ? 'Sugerido pela sequência da EP. Pode alterar.' : undefined}
          >
            <input
              id="nome"
              name="nome"
              value={valores.nome}
              maxLength={150}
              onChange={(evento) => {
                setNomeAutomatico(false)
                alterar(evento)
              }}
              required
            />
          </Campo>
        </div>

        <Campo rotulo="Descrição" nome="descricao" erro={erros.descricao}>
          <textarea
            id="descricao"
            name="descricao"
            rows={4}
            maxLength={500}
            value={valores.descricao}
            onChange={alterar}
          />
        </Campo>

        <div className="formulario__linha formulario__linha--3">
          <Campo rotulo="Status" nome="status" erro={erros.status} obrigatorio>
            <select id="status" name="status" value={valores.status} onChange={alterar}>
              {STATUS.map(([valor, texto]) => (
                <option key={valor} value={valor}>
                  {texto}
                </option>
              ))}
            </select>
          </Campo>

          <Campo rotulo="Início" nome="data_inicio" erro={erros.data_inicio} obrigatorio>
            <input id="data_inicio" name="data_inicio" type="date" value={valores.data_inicio} onChange={alterar} />
          </Campo>

          <Campo rotulo="Fim previsto" nome="data_fim_prevista" erro={erros.data_fim_prevista}>
            <input
              id="data_fim_prevista"
              name="data_fim_prevista"
              type="date"
              value={valores.data_fim_prevista}
              min={valores.data_inicio || undefined}
              onChange={alterar}
            />
          </Campo>
        </div>

        <div className="formulario__acoes">
          <Link to={voltarPara} className="botao botao--fantasma">
            Cancelar
          </Link>
          <button type="submit" className="botao botao--primario" disabled={enviando}>
            {enviando ? 'Salvando...' : editando ? 'Salvar alterações' : 'Criar projeto'}
          </button>
        </div>
      </form>
    </section>
  )
}
