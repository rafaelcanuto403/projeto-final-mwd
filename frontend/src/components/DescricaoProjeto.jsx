export default function DescricaoProjeto({ descricao, className }) {
  const texto = descricao?.trim()
  return (
    <p className={[className, !texto && 'sem-descricao'].filter(Boolean).join(' ')}>
      {texto || 'No momento, projeto sem descrição.'}
    </p>
  )
}
