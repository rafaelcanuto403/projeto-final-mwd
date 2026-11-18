export default function Campo({ rotulo, nome, erro, obrigatorio = false, dica, children }) {
  const mensagens = Array.isArray(erro) ? erro.join(' ') : erro

  return (
    <div className={`campo ${mensagens ? 'campo--erro' : ''}`}>
      <label htmlFor={nome}>
        {rotulo}
        {obrigatorio && <span className="campo__obrigatorio"> *</span>}
      </label>
      {children}
      {mensagens ? <p className="campo__mensagem">{mensagens}</p> : dica && <p className="campo__dica">{dica}</p>}
    </div>
  )
}
