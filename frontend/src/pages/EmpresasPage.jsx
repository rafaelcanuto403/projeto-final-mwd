import { Link } from 'react-router-dom'
import EmpresaFaixa from '../components/EmpresaFaixa.jsx'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import { consultas, useConsultas } from '../api/queries.js'
import { usePode } from '../auth/useAuth.js'

export default function EmpresasPage() {
  const pode = usePode()
  const { dados, carregando, erro } = useConsultas([consultas.empresas(), consultas.projetos()])
  const [empresas, projetos] = dados
  // Só mostra a lista quando as duas consultas chegaram (a faixa de cada EP usa os projetos).
  const pronto = !carregando && !erro

  return (
    <section>
      <div className="secao-cabecalho">
        <h2 className="titulo-secao">Empresas parceiras</h2>
        <div className="acoes">
          {pode('empresa', 'criar') && (
            <Link to="/projetos/empresa/nova" className="botao botao--fantasma">
              + Nova empresa
            </Link>
          )}
          {pode('projeto', 'criar') && (
            <Link to="/projetos/novo" className="botao botao--primario">
              + Novo projeto
            </Link>
          )}
        </div>
      </div>

      {carregando && <Carregando />}
      {erro && <Erro mensagem={erro} />}
      {pronto && empresas.length === 0 && <Vazio texto="Nenhuma empresa parceira cadastrada." />}

      {pronto && empresas.length > 0 && (
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
