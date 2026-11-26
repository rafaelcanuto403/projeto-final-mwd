"""Prévia (miniatura) da primeira página de cada documento.

Gerada no backend uma única vez e guardada em MEDIA_ROOT/previas/, para a listagem não
precisar baixar os arquivos inteiros. O arquivo da prévia leva o id do documento e um hash
do nome do arquivo: se o arquivo do documento mudar, a prévia antiga deixa de valer.
"""

import hashlib
import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pypdfium2 as pdfium
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageDraw, ImageFont, ImageOps

PASTA = 'previas'
# Mudar a versão faz todas as prévias em cache serem refeitas (ex.: ao melhorar a qualidade).
VERSAO = 2
# 2x o tamanho em que o card mostra a prévia, para ficar nítida em telas com zoom/alta densidade.
LARGURA = 960
ALTURA = 1280  # proporção de uma folha A4
MAX_ENTRADA_ZIP = 8 * 1024 * 1024  # não lê entradas maiores (proteção contra "zip bomb")
MAX_TEXTO = 64 * 1024
MAX_PIXELS = 80_000_000  # ~80 MP: acima disso a imagem fica sem prévia

# Formatos com prévia. Os demais (.doc, .xls, .ppt) mostram só o ícone da extensão.
EXTENSOES_COM_PREVIA = {
    '.pdf', '.png', '.jpg', '.jpeg', '.txt', '.csv', '.zip',
    '.docx', '.xlsx', '.pptx', '.odt', '.ods', '.odp',
}

# Miniaturas que o Word/Excel/PowerPoint/LibreOffice salvam dentro do próprio arquivo.
MINIATURAS_EMBUTIDAS = ['docProps/thumbnail.jpeg', 'docProps/thumbnail.png', 'Thumbnails/thumbnail.png']

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

# A mesma fonte do site (licença OFL, em api/fontes/). A fonte padrão do Pillow não tem acentos.
FONTE = Path(__file__).resolve().parent / 'fontes' / 'SourceSans3-Regular.ttf'


def tem_previa(documento):
    return Path(documento.arquivo.name).suffix.lower() in EXTENSOES_COM_PREVIA


def caminho_da_previa(documento):
    assinatura = hashlib.sha1(documento.arquivo.name.encode()).hexdigest()[:10]
    return f'{PASTA}/{documento.pk}-{assinatura}-v{VERSAO}.webp'


def obter_previa(documento):
    """Devolve o caminho (no storage) da prévia, gerando-a se preciso; None se não houver."""
    if not tem_previa(documento):
        return None
    caminho = caminho_da_previa(documento)
    if default_storage.exists(caminho):
        return caminho

    try:
        with documento.arquivo.open('rb') as arquivo:
            imagem = gerar_imagem(extensao_de(documento), arquivo.read())
    except Exception:  # arquivo corrompido ou malformado: fica sem prévia, sem derrubar a API
        return None
    if imagem is None:
        return None

    apagar_previas(documento.pk)  # remove prévias antigas (outro arquivo ou outra versão)
    return default_storage.save(caminho, ContentFile(codificar(imagem, extensao_de(documento))))


def extensao_de(documento):
    return Path(documento.arquivo.name).suffix.lower()


def codificar(imagem, extensao):
    """WebP sem perda para páginas, texto e capturas de tela (bordas de letras ficam nítidas);
    com perda, em qualidade alta, só para fotos (JPG), onde o sem perda ficaria pesado."""
    saida = io.BytesIO()
    if extensao in {'.jpg', '.jpeg'}:
        imagem.convert('RGB').save(saida, 'WEBP', quality=90, method=4)
    else:
        # No modo sem perda, "quality" é o esforço de compressão: 75/4 dá quase o mesmo tamanho
        # que o máximo (100/6) em ~1/20 do tempo.
        imagem.convert('RGB').save(saida, 'WEBP', lossless=True, quality=75, method=4)
    return saida.getvalue()


def apagar_previas(documento_id):
    try:
        _, arquivos = default_storage.listdir(PASTA)
    except FileNotFoundError:
        return
    for nome in arquivos:
        if nome.startswith(f'{documento_id}-'):
            default_storage.delete(f'{PASTA}/{nome}')


# ---- geração por formato ----------------------------------------------------------

def gerar_imagem(extensao, dados):
    if extensao == '.pdf':
        return de_pdf(dados)
    if extensao in {'.png', '.jpg', '.jpeg'}:
        return de_imagem(dados)
    if extensao in {'.txt', '.csv'}:
        return de_texto(decodificar(dados[:MAX_TEXTO]).splitlines())
    if extensao == '.zip':
        return de_zip(dados)
    if extensao in {'.docx', '.xlsx', '.pptx', '.odt', '.ods', '.odp'}:
        return de_office(extensao, dados)
    return None


def de_pdf(dados):
    pdf = pdfium.PdfDocument(dados)
    try:
        pagina = pdf[0]
        largura, altura = pagina.get_size()
        # Escala pela largura, mas sem deixar páginas de proporção absurda virarem imagens gigantes.
        escala = min(LARGURA / largura, 3 * ALTURA / altura, 4)
        return pagina.render(scale=escala).to_pil()
    finally:
        pdf.close()


def de_imagem(dados):
    imagem = Image.open(io.BytesIO(dados))
    if imagem.width * imagem.height > MAX_PIXELS:
        return None
    limite = (LARGURA, 2 * LARGURA)
    imagem.draft('RGB', limite)  # JPEG: já decodifica em tamanho reduzido
    imagem = ImageOps.exif_transpose(imagem)  # respeita a rotação de fotos de celular
    # Lanczos e sem "reducing_gap": redução mais lenta, porém bem mais nítida para texto.
    imagem.thumbnail(limite, Image.Resampling.LANCZOS, reducing_gap=None)
    return imagem


def de_office(extensao, dados):
    with zipfile.ZipFile(io.BytesIO(dados)) as pacote:
        nomes = set(pacote.namelist())
        for nome in MINIATURAS_EMBUTIDAS:
            if nome in nomes and pacote.getinfo(nome).file_size <= MAX_ENTRADA_ZIP:
                return de_imagem(pacote.read(nome))
        # Sem miniatura embutida: no Word, monta a primeira página com o texto do documento.
        if extensao == '.docx' and 'word/document.xml' in nomes:
            if pacote.getinfo('word/document.xml').file_size <= MAX_ENTRADA_ZIP:
                return de_texto(paragrafos_do_docx(pacote.read('word/document.xml')))
    return None


def paragrafos_do_docx(xml):
    raiz = ElementTree.fromstring(xml)
    return [''.join(t.text or '' for t in p.iter(f'{W}t')) for p in raiz.iter(f'{W}p')]


def de_zip(dados):
    with zipfile.ZipFile(io.BytesIO(dados)) as pacote:
        arquivos = [info.filename for info in pacote.infolist() if not info.is_dir()]
    return de_texto([f'{len(arquivos)} arquivo(s):', ''] + [f'• {nome}' for nome in sorted(arquivos)])


def decodificar(dados):
    for codificacao in ('utf-8-sig', 'cp1252'):
        try:
            return dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return dados.decode('latin-1')


def de_texto(linhas):
    """Desenha as linhas numa "folha" branca, quebrando as que não cabem na largura."""
    escala = LARGURA / 480  # medidas pensadas para uma folha de 480 px
    folha = Image.new('RGB', (LARGURA, ALTURA), 'white')
    desenho = ImageDraw.Draw(folha)
    fonte = ImageFont.truetype(str(FONTE), round(17 * escala))
    margem, altura_linha = round(32 * escala), round(23 * escala)
    largura_util = LARGURA - 2 * margem
    y = margem

    for linha in linhas:
        for trecho in quebrar(desenho, linha.replace('\t', '    '), fonte, largura_util):
            if y + altura_linha > ALTURA - margem:
                return folha
            desenho.text((margem, y), trecho, fill='#333333', font=fonte)
            y += altura_linha
    return folha


def quebrar(desenho, linha, fonte, largura):
    if not linha.strip():
        return ['']
    trechos, atual = [], ''
    for palavra in linha.split(' '):
        tentativa = f'{atual} {palavra}' if atual else palavra
        if desenho.textlength(tentativa, font=fonte) <= largura:
            atual = tentativa
            continue
        if atual:
            trechos.append(atual)
        # palavra maior que a linha inteira: corta no tamanho que cabe
        while desenho.textlength(palavra, font=fonte) > largura:
            corte = len(palavra)
            while corte > 1 and desenho.textlength(palavra[:corte], font=fonte) > largura:
                corte -= 1
            trechos.append(palavra[:corte])
            palavra = palavra[corte:]
        atual = palavra
    trechos.append(atual)
    return trechos
