import { Link } from 'react-router-dom'

export default function NaoEncontrada() {
  return (
    <section className="nao-encontrada">
      <p className="nao-encontrada__codigo">404</p>
      <h1>Página não encontrada</h1>
      <p className="texto-suave">O endereço pode estar errado ou o item pode ter sido excluído.</p>
      <Link to="/" className="botao botao--primario">
        Voltar ao início
      </Link>
    </section>
  )
}
