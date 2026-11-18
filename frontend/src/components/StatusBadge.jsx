export default function StatusBadge({ status, texto }) {
  return (
    <span className={`status status--${status}`}>
      <span className="status__ponto" aria-hidden="true" />
      {texto}
    </span>
  )
}
