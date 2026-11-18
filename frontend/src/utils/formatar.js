export function formatarData(iso) {
  if (!iso) return '—'
  const [ano, mes, dia] = iso.split('-')
  return `${dia}/${mes}/${ano}`
}

export function formatarDuracao(inicioIso, fimIso) {
  if (!inicioIso || !fimIso) return null
  const dias = Math.round((new Date(fimIso) - new Date(inicioIso)) / 86_400_000)
  if (dias < 45) return `${dias} ${dias === 1 ? 'dia' : 'dias'}`
  const meses = Math.round(dias / 30)
  return `${meses} ${meses === 1 ? 'mês' : 'meses'}`
}

export function iniciais(nome) {
  const partes = nome.trim().split(/\s+/)
  const primeira = partes[0]?.[0] ?? ''
  const ultima = partes.length > 1 ? partes.at(-1)[0] : ''
  return (primeira + ultima).toUpperCase()
}

export function formatarTamanho(bytes) {
  if (bytes == null) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} MB`
}
