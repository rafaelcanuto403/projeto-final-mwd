import { Link } from 'react-router-dom'
import EmpresaCard from '../components/EmpresaCard.jsx'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import { useApi } from '../hooks/useApi.js'
import { api } from '../services/api.js'

export default function EmpresasPage() {
  const { dados: empresas, carregando, erro } = useApi(api.listarEmpresas)

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
        <div className="grade-empresas">
          {empresas.map((empresa) => (
            <EmpresaCard key={empresa.id} empresa={empresa} />
          ))}
        </div>
      )}
    </section>
  )
}
