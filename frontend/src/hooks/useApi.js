import { useEffect, useState } from 'react'

// Executa uma chamada à API e controla os estados de carregamento e erro.
// `dependencias` funciona como no useEffect: muda → busca de novo.
export function useApi(buscar, dependencias = []) {
  const [estado, setEstado] = useState({ dados: null, carregando: true, erro: null })

  // As dependências vêm de quem chama o hook, por isso os avisos abaixo são desativados
  // oxlint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    let ativo = true // evita atualizar o estado se o componente já saiu da tela
    setEstado((anterior) => ({ ...anterior, carregando: true, erro: null }))

    buscar()
      .then((dados) => ativo && setEstado({ dados, carregando: false, erro: null }))
      .catch((erro) => ativo && setEstado({ dados: null, carregando: false, erro: erro.message }))

    return () => {
      ativo = false
    }
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, dependencias)

  return estado
}
