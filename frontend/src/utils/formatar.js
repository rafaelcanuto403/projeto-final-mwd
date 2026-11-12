// "2026-03-15" → "15/03/2026"
export function formatarData(iso) {
  if (!iso) return '—'
  const [ano, mes, dia] = iso.split('-')
  return `${dia}/${mes}/${ano}`
}

// Duração aproximada entre duas datas ISO, em meses ("3 meses") ou dias ("20 dias")
export function formatarDuracao(inicioIso, fimIso) {
  if (!inicioIso || !fimIso) return null
  const dias = Math.round((new Date(fimIso) - new Date(inicioIso)) / 86_400_000)
  if (dias < 45) return `${dias} ${dias === 1 ? 'dia' : 'dias'}`
  const meses = Math.round(dias / 30)
  return `${meses} ${meses === 1 ? 'mês' : 'meses'}`
}

// "Maria Luísa Bastiani" → "MB"
export function iniciais(nome) {
  const partes = nome.trim().split(/\s+/)
  const primeira = partes[0]?.[0] ?? ''
  const ultima = partes.length > 1 ? partes.at(-1)[0] : ''
  return (primeira + ultima).toUpperCase()
}
