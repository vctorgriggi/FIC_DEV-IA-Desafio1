"""Geração ou edição da peça visual de orientação (RF10).

O modelo gera só a ilustração, sem texto; o texto da peça e o selo de conteúdo
sintético são aplicados por código. Modelo de imagem erra letras com
frequência, e aqui o texto vem dos dados do caso e precisa sair exato.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .audit import agora_iso
from .config import Config
from .entradas import TIPOS_MIME
from .llm_client import ClienteLLM, RespostaLLM

CAMPOS_ESPECIFICACAO = ("sujeito", "composicao", "estilo", "iluminacao", "proporcao", "restricoes", "texto")
PROPORCOES = ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9")
# Valem para toda peça, mesmo que a especificação esqueça (RF10 e seção 13 do enunciado).
RESTRICOES_OBRIGATORIAS = (
    "sem texto, letras ou números na imagem (o texto é aplicado depois)",
    "sem pessoas reais, rostos identificáveis ou figuras públicas",
    "sem brasões, bandeiras, logotipos ou símbolos oficiais",
)
# Só a resolução 1K tem preço por imagem no config.json.
TAMANHO_IMAGEM = "1K"

LARGURA_PECA = 1080
MARGEM = 64
CORES = {"fundo": "#ffffff", "titulo": "#0b3d6e", "corpo": "#1f2933", "faixa": "#1f2933", "faixa_texto": "#ffffff"}
FONTES = {
    False: (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ),
    True: (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ),
}


class ErroPeca(ValueError):
    pass


@dataclass
class PecaVisual:
    caminho: Path
    prompt: str
    modelo: str
    data_geracao: str
    nota_proveniencia: str
    resposta: RespostaLLM | None = None
    ilustracao_original: Path | None = None


def validar_especificacao(especificacao: dict) -> None:
    faltando = [campo for campo in CAMPOS_ESPECIFICACAO if not especificacao.get(campo)]
    if faltando:
        raise ErroPeca(f"Especificação sem: {', '.join(faltando)}.")
    if especificacao["proporcao"] not in PROPORCOES:
        raise ErroPeca(f"Proporção {especificacao['proporcao']} não aceita. Opções: {', '.join(PROPORCOES)}.")
    if not isinstance(especificacao["restricoes"], list):
        raise ErroPeca("restricoes deve ser uma lista.")
    texto = especificacao["texto"]
    if not isinstance(texto, dict) or not str(texto.get("titulo", "")).strip():
        raise ErroPeca("texto.titulo é obrigatório.")
    if not isinstance(texto.get("itens", []), list):
        raise ErroPeca("texto.itens deve ser uma lista.")


def montar_prompt(especificacao: dict, *, edicao: bool) -> str:
    restricoes = list(dict.fromkeys([*RESTRICOES_OBRIGATORIAS, *especificacao["restricoes"]]))
    abertura = (
        "Edite a imagem fornecida para uma peça de orientação institucional fictícia."
        if edicao
        else "Gere uma ilustração para uma peça de orientação institucional fictícia."
    )
    return "\n".join(
        [
            abertura,
            f"Sujeito: {especificacao['sujeito']}",
            f"Composição: {especificacao['composicao']}",
            f"Estilo: {especificacao['estilo']}",
            f"Iluminação: {especificacao['iluminacao']}",
            f"Proporção: {especificacao['proporcao']}",
            "Restrições:",
            *(f"- {r}" for r in restricoes),
        ]
    )


def gerar_peca(
    especificacao: dict,
    destino: Path,
    *,
    imagem_base: Path | None,
    cliente: ClienteLLM,
    config: Config,
) -> PecaVisual:
    """Gera (ou edita `imagem_base`) a ilustração e compõe a peça final em `destino` (PNG).

    A ilustração devolvida pelo modelo fica intacta ao lado, como `<destino>_ilustracao_ia.<ext>`.
    Formato da chamada (fonte: docs oficiais Gemini API, image-generation, out/2026):
    response_format {"type": "image", "aspect_ratio", "image_size"} e a imagem em
    output_image.data (base64). As imagens geradas levam marca d'água SynthID.
    """
    validar_especificacao(especificacao)
    prompt = montar_prompt(especificacao, edicao=imagem_base is not None)
    entrada: str | list[dict] = prompt
    if imagem_base is not None:
        mime = TIPOS_MIME.get(imagem_base.suffix.lower(), "")
        if not mime.startswith("image/"):
            raise ErroPeca(f"Só imagem pode ser editada; {imagem_base.name} não é.")
        dados_base = base64.b64encode(imagem_base.read_bytes()).decode("ascii")
        entrada = [{"type": "text", "text": prompt}, {"type": "image", "data": dados_base, "mime_type": mime}]

    modelo = config.modelo("imagem")
    resposta = cliente.gerar(
        modelo=modelo,
        entrada=entrada,
        formato_resposta={"type": "image", "aspect_ratio": especificacao["proporcao"], "image_size": TAMANHO_IMAGEM},
        saida="imagem",
    )
    saida = resposta.bruta.output_image
    conteudo = base64.b64decode(saida.data)
    extensao = ".jpg" if getattr(saida, "mime_type", "") == "image/jpeg" else ".png"
    original = destino.with_name(f"{destino.stem}_ilustracao_ia{extensao}")
    original.write_bytes(conteudo)

    data_geracao = agora_iso()
    nota = (
        f"Ilustração {'editada' if imagem_base else 'gerada'} por IA ({modelo}, Google Gemini) em {data_geracao}; "
        "texto aplicado por código a partir dos dados do caso fictício. Conteúdo sintético, sem pessoas reais. "
        "A ilustração do modelo carrega marca d'água SynthID."
    )
    selo = f"Ilustração {'editada' if imagem_base else 'gerada'} por IA ({modelo}) — conteúdo sintético, material fictício."
    with Image.open(io.BytesIO(conteudo)) as ilustracao:
        compor_peca(ilustracao, especificacao["texto"], selo).save(destino, format="PNG")

    return PecaVisual(
        caminho=destino,
        prompt=prompt,
        modelo=modelo,
        data_geracao=data_geracao,
        nota_proveniencia=nota,
        resposta=resposta,
        ilustracao_original=original,
    )


def compor_peca(ilustracao: Image.Image, texto: dict, selo: str) -> Image.Image:
    """Ilustração em cima; título, introdução, itens e rodapé embaixo; selo de IA na faixa final."""
    altura_ilustracao = round(ilustracao.height * LARGURA_PECA / ilustracao.width)
    ilustracao = ilustracao.convert("RGB").resize((LARGURA_PECA, altura_ilustracao))
    util = LARGURA_PECA - 2 * MARGEM
    recuo = 40

    fonte_titulo, fonte_corpo, fonte_selo = _fonte(56, True), _fonte(34, False), _fonte(24, False)
    blocos: list[tuple[list[str], ImageFont.FreeTypeFont, str, int]] = [
        (_quebrar(texto["titulo"], fonte_titulo, util), fonte_titulo, CORES["titulo"], 0)
    ]
    if texto.get("introducao"):
        blocos.append((_quebrar(texto["introducao"], fonte_corpo, util), fonte_corpo, CORES["corpo"], 0))
    for item in texto.get("itens", []):
        blocos.append((_quebrar(item, fonte_corpo, util - recuo), fonte_corpo, CORES["corpo"], recuo))
    if texto.get("rodape"):
        blocos.append((_quebrar(texto["rodape"], fonte_corpo, util), fonte_corpo, CORES["corpo"], 0))
    linhas_selo = _quebrar(selo, fonte_selo, util)

    espaco = 24
    altura_texto = sum(len(linhas) * _altura_linha(fonte) + espaco for linhas, fonte, _, _ in blocos)
    altura_faixa = len(linhas_selo) * _altura_linha(fonte_selo) + 2 * espaco
    peca = Image.new("RGB", (LARGURA_PECA, altura_ilustracao + MARGEM + altura_texto + MARGEM + altura_faixa), CORES["fundo"])
    peca.paste(ilustracao, (0, 0))
    desenho = ImageDraw.Draw(peca)

    y = altura_ilustracao + MARGEM
    for linhas, fonte, cor, deslocamento in blocos:
        if deslocamento:
            desenho.text((MARGEM, y), "•", font=fonte, fill=cor)
        for linha in linhas:
            desenho.text((MARGEM + deslocamento, y), linha, font=fonte, fill=cor)
            y += _altura_linha(fonte)
        y += espaco

    y_faixa = peca.height - altura_faixa
    desenho.rectangle((0, y_faixa, LARGURA_PECA, peca.height), fill=CORES["faixa"])
    y = y_faixa + espaco
    for linha in linhas_selo:
        desenho.text((MARGEM, y), linha, font=fonte_selo, fill=CORES["faixa_texto"])
        y += _altura_linha(fonte_selo)
    return peca


def _fonte(tamanho: int, negrito: bool) -> ImageFont.FreeTypeFont:
    for caminho in FONTES[negrito]:
        if Path(caminho).is_file():
            return ImageFont.truetype(caminho, tamanho)
    # A fonte embutida do Pillow não tem acentos; melhor parar que imprimir "Matr□cula".
    raise ErroPeca("Nenhuma fonte com acentos encontrada (Arial ou DejaVu Sans). Instale uma delas.")


def _altura_linha(fonte: ImageFont.FreeTypeFont) -> int:
    return round(fonte.size * 1.3)


def _quebrar(texto: str, fonte: ImageFont.FreeTypeFont, largura: int) -> list[str]:
    linhas: list[str] = []
    atual = ""
    for palavra in texto.split():
        tentativa = f"{atual} {palavra}".strip()
        if atual and fonte.getlength(tentativa) > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = tentativa
    if atual:
        linhas.append(atual)
    return linhas
