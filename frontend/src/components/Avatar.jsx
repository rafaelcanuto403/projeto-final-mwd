import { useState } from 'react'
import { iniciais } from '../utils/formatar.js'

export default function Avatar({ nome, fotoUrl, tamanho = 72 }) {
  const [falhou, setFalhou] = useState(false)
  const estilo = { width: tamanho, height: tamanho, fontSize: tamanho * 0.36 }

  if (!fotoUrl || falhou) {
    return (
      <div className="avatar avatar--iniciais" style={estilo} aria-hidden="true">
        {iniciais(nome)}
      </div>
    )
  }

  return (
    <img
      src={fotoUrl}
      alt=""
      className="avatar"
      style={estilo}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => setFalhou(true)}
    />
  )
}
