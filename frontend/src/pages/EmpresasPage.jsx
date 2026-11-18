import { Link } from 'react-router-dom'
import EmpresaFaixa from '../components/EmpresaFaixa.jsx'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import { api, useApi } from '../api/useApi.js'

export default function EmpresasPage() {
  const { dados, carregando, erro } = useApi(() => Promise.all([api.listarEmpresas(), api.listarProjetos()]))
  const [empresas, projetos] = dados ?? []

  return (
    <section>
      <div className="secao-cabecalho">
        <h2 className="titulo-secao">Empresas parceiras</h2>
        <div className="acoes">
          <Link to="/projetos/empresa/nova" className="botao botao--fantasma">
            + Nova empresa
          </Link>
          <Link to="/projetos/novo" className="botao botao--primario">
            + Novo projeto
          </Link>
        </div>
      </div>

      {carregando && <Carregando />}
      {erro && <Erro mensagem={erro} />}
      {empresas?.length === 0 && <Vazio texto="Nenhuma empresa parceira cadastrada." />}

      {empresas?.length > 0 && (
        <div className="pilha-empresas">
          {empresas.map((empresa) => (
            <EmpresaFaixa
              key={empresa.id}
              empresa={empresa}
              projetos={projetos.filter((p) => p.empresa === empresa.id)}
            />
          ))}
        </div>
      )}
    </section>
  )
}
