import { useState } from 'react'
import { Link } from 'react-router-dom'
import Avatar from '../components/Avatar.jsx'
import { Carregando, Erro, Vazio } from '../components/Estado.jsx'
import { api, useApi } from '../api/useApi.js'

const normalizar = (texto) =>
  texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()

export default function MembrosPage() {
  const { dados: membros, carregando, erro } = useApi(api.listarMembros)
  const [busca, setBusca] = useState('')

  const termo = normalizar(busca.trim())
  const filtrados = (membros ?? []).filter(
    (m) => !termo || [m.nome, m.sigla, m.cargo].some((texto) => normalizar(texto ?? '').includes(termo)),
  )

  return (
    <section>
      <div className="secao-cabecalho">
        <h2 className="titulo-secao">Membros</h2>
        <div className="acoes">
          <input
            type="search"
            className="busca"
            placeholder="Buscar por nome, sigla ou cargo..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            aria-label="Buscar membros"
          />
          <Link to="/membros/novo" className="botao botao--primario">
            + Novo membro
          </Link>
        </div>
      </div>

      {carregando && <Carregando />}
      {erro && <Erro mensagem={erro} />}
      {membros?.length === 0 && <Vazio texto="Nenhum membro cadastrado." />}
      {membros?.length > 0 && filtrados.length === 0 && <Vazio texto={`Nenhum membro encontrado para "${busca}".`} />}

      <div className="grade-membros">
        {filtrados.map((membro) => (
          <Link key={membro.id} to={`/membros/${membro.id}`} className="membro-card membro-card--link">
            <Avatar nome={membro.nome} fotoUrl={membro.foto_url} />
            <div className="membro-card__nome">
              <h3>{membro.nome}</h3>
              <span className="membro-card__sigla">{membro.sigla}</span>
            </div>
            {membro.cargo && <span className="membro-card__cargo">{membro.cargo}</span>}
            <span className="texto-suave">
              {membro.total_projetos} {membro.total_projetos === 1 ? 'projeto' : 'projetos'}
            </span>
          </Link>
        ))}
      </div>
    </section>
  )
}
