"""Visão e OCR (RF08)."""

from __future__ import annotations

from .config import Config
from .entradas import ArquivoEntrada
from .llm_client import ClienteLLM
from .tipos import PendenteDeImplementacao, TextoExtraido


def extrair_texto(arquivo: ArquivoEntrada, *, cliente: ClienteLLM, config: Config) -> TextoExtraido:
    """RF08 — parte: imagem.

    Esperado: texto bruto preservado, versão corrigida sem alterar o sentido e
    trechos ilegíveis ou incertos em trechos_incertos. O arquivo original não é
    alterado; os dados críticos passam por confirmação humana no fluxo.

    Formato aceito pela Interactions API (conferido no SDK google-genai 2.31.0):
    PDF  -> {"type": "document", "data": <base64>, "mime_type": "application/pdf"}
    foto -> {"type": "image", "data": <base64>, "mime_type": arquivo.mime_type}
    com modelo config.modelo("visao").
    """
    raise PendenteDeImplementacao("RF08", "imagem")
