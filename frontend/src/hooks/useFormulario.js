import { useState } from 'react'
import { ApiError } from '../services/api.js'

// Controla os valores de um formulário, o envio e os erros vindos da API.
export function useFormulario(valoresIniciais) {
  const [valores, setValores] = useState(valoresIniciais)
  const [erros, setErros] = useState({})
  const [erroGeral, setErroGeral] = useState(null)
  const [enviando, setEnviando] = useState(false)

  // Para usar direto no onChange dos campos: <input name="nome" onChange={alterar} />
  function alterar(evento) {
    const { name, value } = evento.target
    setValores((atuais) => ({ ...atuais, [name]: value }))
    setErros((atuais) => ({ ...atuais, [name]: undefined }))
  }

  // Executa `acao` (ex.: salvar na API) e distribui os erros pelos campos
  async function enviar(acao) {
    setEnviando(true)
    setErros({})
    setErroGeral(null)
    try {
      return await acao()
    } catch (erro) {
      if (erro instanceof ApiError && Object.keys(erro.campos).length > 0) {
        const { non_field_errors: gerais, ...porCampo } = erro.campos
        setErros(porCampo)
        setErroGeral(gerais?.join(' ') ?? erro.message)
      } else {
        setErroGeral(erro.message)
      }
      return undefined
    } finally {
      setEnviando(false)
    }
  }

  return { valores, setValores, alterar, erros, erroGeral, enviando, enviar }
}
