"""Ingestão do acervo (RF17, RF18): manifesto, extração de texto e divisão em trechos.

O manifesto (dados/acervo/acervo.json) é o contrato entre quem escreve o
acervo e quem o indexa: cada documento tem id, título, versão e arquivo.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .config import Config
from .entradas import ArquivoInvalido
from .schemas import DocumentoAcervo, Trecho
from .tipos import PendenteDeImplementacao


def ler_manifesto(config: Config) -> list[DocumentoAcervo]:
    """Documentos do acervo, validados; arquivo ausente, extensão fora da lista ou id repetido é erro."""
    caminho = config.raiz / config.dados["acervo"]["manifesto"]
    if not caminho.is_file():
        raise ArquivoInvalido(f"Manifesto do acervo não encontrado: {config.relativo(caminho)}.")
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
        documentos = [DocumentoAcervo(**item) for item in bruto["documentos"]]
    except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as erro:
        raise ArquivoInvalido(f"Manifesto do acervo inválido: {erro}") from None
    ids = [d.id for d in documentos]
    if len(ids) != len(set(ids)):
        raise ArquivoInvalido("Manifesto do acervo com id de documento repetido.")
    extensoes = config.dados["acervo"]["extensoes"]
    for documento in documentos:
        arquivo = caminho_documento(config, documento)
        if not arquivo.is_file():
            raise ArquivoInvalido(f"Documento {documento.id} aponta para arquivo inexistente: {documento.arquivo}.")
        if arquivo.suffix.lower() not in extensoes:
            raise ArquivoInvalido(f"Documento {documento.id}: extensão {arquivo.suffix} fora de {', '.join(extensoes)}.")
    return documentos


def caminho_documento(config: Config, documento: DocumentoAcervo) -> Path:
    return config.caminho("acervo") / documento.arquivo


def extrair_texto(documento: DocumentoAcervo, *, config: Config) -> list[tuple[int | None, str]]:
    """RF17 — parte: índice.

    Esperado:
    - TXT: um único bloco, página None; PDF textual: um bloco por página, com o número da página (pypdf);
    - validar tamanho (acervo.tamanho_max_mb) antes de ler; PDF sem texto extraível é erro claro, não lista vazia;
    - não alterar o arquivo original.
    """
    raise PendenteDeImplementacao("RF17", "índice")


def dividir(documento: DocumentoAcervo, paginas: list[tuple[int | None, str]], *, perfil: str, config: Config) -> list[Trecho]:
    """RF18 — parte: índice.

    Esperado:
    - tamanho e sobreposição do perfil em config["indice"]["chunking"][perfil], na unidade declarada lá;
    - cada Trecho com documento, versão, hash do arquivo, página, seção (quando houver título de seção) e chunking=perfil;
    - id determinístico do trecho (mesmo documento, versão e posição dão o mesmo id): é o que impede duplicação ao reindexar.
    """
    raise PendenteDeImplementacao("RF18", "índice")
