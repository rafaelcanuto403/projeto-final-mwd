export function Carregando() {
  return <p className="estado">Carregando...</p>
}

export function Erro({ mensagem }) {
  return (
    <p className="estado estado--erro">
      {mensagem}
      {mensagem?.includes('conectar') && (
        <>
          {' '}
          Verifique se o backend está rodando em <code>127.0.0.1:8000</code>.
        </>
      )}
    </p>
  )
}

export function Vazio({ texto }) {
  return <p className="estado">{texto}</p>
}
