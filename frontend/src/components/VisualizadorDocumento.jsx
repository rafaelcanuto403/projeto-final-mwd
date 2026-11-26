import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { consultas, extensaoDe, useBaixarDocumento } from '../api/queries.js'
import { formatarTamanho } from '../utils/formatar.js'

// Como cada formato é exibido. O tipo (MIME) do arquivo é definido pela extensão em
// api/queries.js, nunca pelo conteúdo, para um arquivo malicioso não abrir como página HTML.
const VISUALIZADORES = {
  pdf: 'pdf',
  png: 'imagem',
  jpg: 'imagem',
  jpeg: 'imagem',
  txt: 'texto',
  csv: 'csv',
  docx: 'docx',
  xlsx: 'planilha',
  zip: 'zip',
}

const MAX_LINHAS = 500
const MAX_TEXTO = 1024 * 1024

export default function VisualizadorDocumento({ documento }) {
  const [erroAoBaixar, setErroAoBaixar] = useState(null)
  const extensao = extensaoDe(documento)
  const visualizador = VISUALIZADORES[extensao]
  const baixarDocumento = useBaixarDocumento()

  // Formatos sem pré-visualização não são baixados à toa: só se a pessoa clicar em Baixar.
  // Fechar e abrir de novo o mesmo documento (ou baixá-lo depois) usa o arquivo do cache.
  const { data: arquivo, error } = useQuery({ ...consultas.arquivo(documento), enabled: Boolean(visualizador) })
  const erro = erroAoBaixar ?? error?.message

  async function baixar() {
    try {
      await baixarDocumento(documento)
    } catch (e) {
      setErroAoBaixar(e.message)
    }
  }

  return (
    <div className="visualizador">
      <div className="visualizador__barra">
        <span className="texto-suave">
          {documento.tipo_display} · {documento.nome_arquivo}
          {documento.tamanho != null && ` · ${formatarTamanho(documento.tamanho)}`}
        </span>
        <button type="button" className="botao botao--fantasma botao--pequeno" onClick={baixar}>
          Baixar
        </button>
      </div>

      <div className="visualizador__area">
        {erro ? (
          <p className="estado estado--erro">{erro}</p>
        ) : !visualizador ? (
          <SemVisualizacao extensao={extensao} aoBaixar={baixar} />
        ) : !arquivo ? (
          <p className="estado">Carregando documento...</p>
        ) : (
          <Conteudo tipo={visualizador} arquivo={arquivo} titulo={documento.titulo} />
        )}
      </div>
    </div>
  )
}

function Conteudo({ tipo, arquivo, titulo }) {
  switch (tipo) {
    case 'pdf':
      return <iframe src={arquivo.url} title={titulo} className="visualizador__pdf" />
    case 'imagem':
      return <img src={arquivo.url} alt={titulo} className="visualizador__imagem" />
    case 'texto':
      return <Texto blob={arquivo.blob} />
    case 'csv':
      return <Csv blob={arquivo.blob} />
    case 'docx':
      return <Docx blob={arquivo.blob} />
    case 'planilha':
      return <Planilha blob={arquivo.blob} />
    case 'zip':
      return <Zip blob={arquivo.blob} />
    default:
      return null
  }
}

/** Carrega algo a partir do blob e trata carregando/erro de um jeito só. */
function useLeitura(ler, blob) {
  const [estado, setEstado] = useState({ dados: null, erro: null })
  useEffect(() => {
    let ativo = true
    ler(blob)
      .then((dados) => ativo && setEstado({ dados, erro: null }))
      .catch(() => ativo && setEstado({ dados: null, erro: 'Não foi possível ler este arquivo.' }))
    return () => {
      ativo = false
    }
  }, [ler, blob])
  return estado
}

function Leitura({ estado, children }) {
  if (estado.erro) return <p className="estado estado--erro">{estado.erro}</p>
  if (!estado.dados) return <p className="estado">Preparando visualização...</p>
  return children(estado.dados)
}

async function lerTexto(blob) {
  const texto = await blob.slice(0, MAX_TEXTO).text()
  return { texto, cortado: blob.size > MAX_TEXTO }
}

function Texto({ blob }) {
  return (
    <Leitura estado={useLeitura(lerTexto, blob)}>
      {({ texto, cortado }) => (
        <>
          <pre className="visualizador__texto">{texto}</pre>
          {cortado && <Aviso texto="Mostrando só o primeiro 1 MB. Baixe o arquivo para ver tudo." />}
        </>
      )}
    </Leitura>
  )
}

/** CSV simples (RFC 4180): aspas, aspas duplicadas e separador , ou ; detectado na 1ª linha. */
function separarCsv(texto) {
  const primeira = texto.slice(0, texto.indexOf('\n') >>> 0)
  const separador = (primeira.match(/;/g)?.length ?? 0) > (primeira.match(/,/g)?.length ?? 0) ? ';' : ','
  const linhas = [[]]
  let campo = ''
  let entreAspas = false
  for (let i = 0; i < texto.length; i++) {
    const c = texto[i]
    if (entreAspas) {
      if (c === '"' && texto[i + 1] === '"') campo += texto[++i]
      else if (c === '"') entreAspas = false
      else campo += c
    } else if (c === '"') entreAspas = true
    else if (c === separador) {
      linhas.at(-1).push(campo)
      campo = ''
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && texto[i + 1] === '\n') i++
      linhas.at(-1).push(campo)
      campo = ''
      linhas.push([])
    } else campo += c
  }
  linhas.at(-1).push(campo)
  return linhas.filter((linha) => linha.some((valor) => valor !== ''))
}

async function lerCsv(blob) {
  return separarCsv((await blob.slice(0, MAX_TEXTO).text()).replace(/^﻿/, ''))
}

function Csv({ blob }) {
  return <Leitura estado={useLeitura(lerCsv, blob)}>{(linhas) => <Tabela linhas={linhas} />}</Leitura>
}

async function lerPlanilha(blob) {
  const { default: lerXlsx } = await import('read-excel-file/browser')
  return lerXlsx(blob)
}

function Planilha({ blob }) {
  const [aba, setAba] = useState(0)
  return (
    <Leitura estado={useLeitura(lerPlanilha, blob)}>
      {(abas) => (
        <>
          {abas.length > 1 && (
            <div className="visualizador__abas" role="tablist">
              {abas.map(({ sheet }, indice) => (
                <button
                  key={sheet}
                  type="button"
                  role="tab"
                  aria-selected={indice === aba}
                  className={`visualizador__aba ${indice === aba ? 'visualizador__aba--ativa' : ''}`}
                  onClick={() => setAba(indice)}
                >
                  {sheet}
                </button>
              ))}
            </div>
          )}
          <Tabela linhas={abas[aba]?.data ?? []} />
        </>
      )}
    </Leitura>
  )
}

function formatarCelula(valor) {
  if (valor == null) return ''
  if (valor instanceof Date) return valor.toLocaleDateString('pt-BR')
  return String(valor)
}

function Tabela({ linhas }) {
  if (linhas.length === 0) return <p className="estado">Arquivo vazio.</p>
  const [cabecalho, ...corpo] = linhas.slice(0, MAX_LINHAS + 1)
  return (
    <>
      <div className="visualizador__tabela">
        <table>
          <thead>
            <tr>
              {cabecalho.map((valor, i) => (
                <th key={i}>{formatarCelula(valor)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {corpo.map((linha, i) => (
              <tr key={i}>
                {linha.map((valor, j) => (
                  <td key={j}>{formatarCelula(valor)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {linhas.length > MAX_LINHAS + 1 && (
        <Aviso texto={`Mostrando as primeiras ${MAX_LINHAS} linhas. Baixe o arquivo para ver tudo.`} />
      )}
    </>
  )
}

function Docx({ blob }) {
  const corpo = useRef(null)
  const estilos = useRef(null)
  const [estado, setEstado] = useState('carregando')

  useEffect(() => {
    let ativo = true
    import('docx-preview')
      .then(({ renderAsync }) =>
        renderAsync(blob, corpo.current, estilos.current, {
          className: 'docx',
          inWrapper: true,
          ignoreLastRenderedPageBreak: true,
        }),
      )
      .then(() => {
        if (!ativo) return
        // Links do documento só abrem se forem http(s) ou e-mail, e sempre em outra aba.
        for (const link of corpo.current.querySelectorAll('a[href]')) {
          if (/^(https?:|mailto:)/i.test(link.getAttribute('href'))) {
            Object.assign(link, { target: '_blank', rel: 'noopener noreferrer' })
          } else if (!link.getAttribute('href').startsWith('#')) {
            link.removeAttribute('href')
          }
        }
        setEstado('pronto')
      })
      .catch(() => ativo && setEstado('erro'))
    return () => {
      ativo = false
    }
  }, [blob])

  return (
    <>
      {estado === 'carregando' && <p className="estado">Preparando visualização...</p>}
      {estado === 'erro' && <p className="estado estado--erro">Não foi possível ler este arquivo.</p>}
      <div ref={estilos} />
      <div ref={corpo} className="visualizador__docx" />
    </>
  )
}

async function lerZip(blob) {
  const { default: JSZip } = await import('jszip')
  const zip = await JSZip.loadAsync(blob)
  return Object.values(zip.files)
    .filter((entrada) => !entrada.dir)
    .map((entrada) => ({ nome: entrada.name, tamanho: entrada._data?.uncompressedSize }))
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
}

function Zip({ blob }) {
  return (
    <Leitura estado={useLeitura(lerZip, blob)}>
      {(entradas) => (
        <>
          <p className="texto-suave">
            {entradas.length} {entradas.length === 1 ? 'arquivo' : 'arquivos'} no ZIP. Baixe para extrair.
          </p>
          <ul className="visualizador__zip">
            {entradas.map(({ nome, tamanho }) => (
              <li key={nome}>
                <span>{nome}</span>
                {tamanho != null && <span className="texto-suave">{formatarTamanho(tamanho)}</span>}
              </li>
            ))}
          </ul>
        </>
      )}
    </Leitura>
  )
}

function SemVisualizacao({ extensao, aoBaixar }) {
  return (
    <div className="visualizador__sem">
      <span className="documento__extensao">{extensao}</span>
      <p>
        Não há pré-visualização para arquivos <strong>.{extensao}</strong> no navegador.
      </p>
      <button type="button" className="botao botao--primario" onClick={aoBaixar}>
        Baixar para abrir
      </button>
    </div>
  )
}

function Aviso({ texto }) {
  return <p className="texto-suave visualizador__aviso">{texto}</p>
}
