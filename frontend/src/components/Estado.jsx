// Mensagens padrão de carregamento, erro e lista vazia
export function Carregando({ texto = 'Carregando...' }) {
  return <p className="estado">{texto}</p>
}

export function Erro({ mensagem }) {
  return (
    <p className="estado estado--erro">
      {mensagem} Verifique se o backend está rodando em <code>127.0.0.1:8000</code>.
    </p>
  )
}

export function Vazio({ texto }) {
  return <p className="estado">{texto}</p>
}
