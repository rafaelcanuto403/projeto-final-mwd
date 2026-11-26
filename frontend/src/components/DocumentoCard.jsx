import { useQuery } from '@tanstack/react-query'
import { consultas } from '../api/queries.js'
import { formatarData, formatarTamanho } from '../utils/formatar.js'

/** Card do documento: a prévia da primeira página abre o documento completo. */
export default function DocumentoCard({ documento, aoAbrir, aoBaixar, aoExcluir }) {
  const extensao = documento.nome_arquivo?.split('.').pop() ?? ''

  return (
    <li className="documento-card">
      <button
        type="button"
        className="documento-card__previa"
        onClick={aoAbrir}
        aria-label={`Abrir ${documento.titulo}`}
        title="Abrir documento"
      >
        {documento.tem_previa ? (
          <Previa documento={documento} extensao={extensao} />
        ) : (
          <Extensao extensao={extensao} />
        )}
        <span className="documento-card__selo">{extensao}</span>
      </button>

      <div className="documento-card__rodape">
        <div className="documento-card__info">
          <strong className="documento-card__titulo" title={documento.titulo}>
            {documento.titulo}
          </strong>
          <span>
            {documento.tipo_display} · {formatarData(documento.enviado_em.slice(0, 10))}
            {documento.tamanho != null && ` · ${formatarTamanho(documento.tamanho)}`}
          </span>
        </div>
        <div className="documento-card__acoes">
          <button
            type="button"
            className="botao botao--icone"
            onClick={aoBaixar}
            aria-label={`Baixar ${documento.titulo}`}
            title="Baixar"
          >
            ↓
          </button>
          {documento.permissoes.excluir && (
            <button
              type="button"
              className="botao botao--icone botao--icone-perigo"
              onClick={aoExcluir}
              aria-label={`Excluir ${documento.titulo}`}
              title="Excluir documento"
            >
              ✕
            </button>
          )}
        </div>
      </div>
    </li>
  )
}

function Previa({ documento, extensao }) {
  // Cache por documento: voltar ao projeto mostra as prévias na hora, sem baixá-las de novo.
  // Falhas passageiras tentam de novo (ver queryClient); 404 = documento sem prévia.
  const { data, isError } = useQuery(consultas.previa(documento))

  if (isError) return <Extensao extensao={extensao} />
  if (!data) return <span className="documento-card__carregando" aria-hidden="true" />
  return (
    <img
      src={data.url}
      alt=""
      className="documento-card__imagem"
      decoding="async"
      onLoad={(evento) => {
        // Imagem muito larga (ex.: print de um trecho de texto): encolhê-la inteira deixaria o
        // texto ilegível. Mostra o começo dela, à esquerda, em tamanho legível.
        const { naturalWidth: largura, naturalHeight: altura } = evento.currentTarget
        evento.currentTarget.classList.toggle('documento-card__imagem--larga', largura / altura > 2)
      }}
    />
  )
}

function Extensao({ extensao }) {
  return <span className="documento-card__extensao">{extensao}</span>
}
