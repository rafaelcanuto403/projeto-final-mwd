import { Link } from 'react-router-dom'

const STATUS = [
  ['em_andamento', 'em andamento'],
  ['planejamento', 'em planejamento'],
  ['concluido', 'concluídos'],
]

export default function EmpresaFaixa({ empresa, projetos }) {
  const { id, nome, logo_url: logoUrl, total_projetos: total } = empresa
  const contar = (status) => projetos.filter((p) => p.status === status).length

  return (
    <Link to={`/projetos/empresa/${id}`} className="empresa-faixa" aria-label={`Projetos com ${nome}`}>
      <div className="empresa-faixa__logo">
        {logoUrl ? <img src={logoUrl} alt="" className="logo-branca" /> : <span>{nome}</span>}
      </div>

      <div className="empresa-faixa__info">
        <h3>{nome}</h3>
        <p className="texto-suave">
          {total} {total === 1 ? 'projeto registrado' : 'projetos registrados'}
        </p>
      </div>

      <ul className="empresa-faixa__status">
        {STATUS.map(([status, texto]) => (
          <li
            key={status}
            className={`empresa-faixa__numero empresa-faixa__numero--${contar(status) ? status : 'zero'}`}
          >
            <strong>{contar(status)}</strong>
            <span>{texto}</span>
          </li>
        ))}
      </ul>
    </Link>
  )
}
