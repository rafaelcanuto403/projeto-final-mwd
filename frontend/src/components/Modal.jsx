import { useEffect, useRef } from 'react'

// Janela sobreposta usando o <dialog> nativo do navegador
// (já cuida de foco, tecla Esc e fundo escurecido).
export default function Modal({ aberto, titulo, aoFechar, children }) {
  const dialogo = useRef(null)

  useEffect(() => {
    const elemento = dialogo.current
    if (aberto && !elemento.open) elemento.showModal()
    if (!aberto && elemento.open) elemento.close()
  }, [aberto])

  return (
    <dialog
      ref={dialogo}
      className="modal"
      onClose={aoFechar}
      // clique no fundo escuro (fora da caixa) fecha
      onClick={(evento) => evento.target === dialogo.current && aoFechar()}
    >
      <div className="modal__caixa">
        <header className="modal__cabecalho">
          <h2>{titulo}</h2>
          <button type="button" className="botao botao--icone" onClick={aoFechar} aria-label="Fechar">
            ✕
          </button>
        </header>
        {aberto && children}
      </div>
    </dialog>
  )
}
