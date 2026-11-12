import { Link } from 'react-router-dom'

export default function EmpresaCard({ empresa }) {
  const { id, nome, logo_url: logoUrl, total_projetos: total } = empresa

  return (
    <Link to={`/projetos/empresa/${id}`} className="empresa-card" aria-label={`Projetos com ${nome}`}>
      <div className="empresa-card__logo">
        {logoUrl ? <img src={logoUrl} alt={nome} className="logo-branca" /> : <span className="empresa-card__nome">{nome}</span>}
      </div>
      <span className="empresa-card__total">
        {total} {total === 1 ? 'projeto' : 'projetos'}
      </span>
    </Link>
  )
}
