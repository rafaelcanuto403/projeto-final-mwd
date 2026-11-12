export default function StatusBadge({ status, texto }) {
  return <span className={`status status--${status}`}>{texto}</span>
}
