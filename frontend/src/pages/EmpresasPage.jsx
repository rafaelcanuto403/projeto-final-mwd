import EmpresaCard from '../components/EmpresaCard.jsx'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import { useApi } from '../hooks/useApi.js'
import { api } from '../services/api.js'

export default function EmpresasPage() {
  const { dados: empresas, carregando, erro } = useApi(api.listarEmpresas)

  return (
    <section>
      <h2 className="titulo-secao">Empresas parceiras</h2>

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
