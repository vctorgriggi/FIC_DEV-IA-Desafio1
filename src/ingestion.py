"""Ingestão do acervo (RF17, RF18): manifesto, extração de texto e divisão em trechos.

O manifesto (dados/acervo/acervo.json) é o contrato entre quem escreve o
acervo e quem o indexa: cada documento tem id, título, versão e arquivo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from .audit import Auditoria
from .config import Config
from .entradas import ArquivoInvalido
from .schemas import DocumentoAcervo, Trecho
from .tipos import PendenteDeImplementacao

if TYPE_CHECKING:
    from .embeddings import IndiceVetorial


def ler_manifesto(config: Config) -> list[DocumentoAcervo]:
    """Documentos do acervo, validados; arquivo ausente, extensão fora da lista, id repetido ou `substitui` inválido é erro."""
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
    for documento in documentos:
        # Um id errado em `substitui` desarmaria a resolução de conflito sem aviso (T10).
        invalidos = [alvo for alvo in documento.substitui if alvo not in ids or alvo == documento.id]
        if invalidos:
            raise ArquivoInvalido(f"Documento {documento.id} substitui id inexistente ou a si mesmo: {', '.join(invalidos)}.")
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
    - id determinístico com o hash: f"{documento.id}:{hash[:12]}:{perfil}:{n}". Mesmo arquivo dá os mesmos ids
      (reindexar não duplica); arquivo mudado dá ids novos, e IndiceVetorial.indexar apaga os antigos.
    """
    raise PendenteDeImplementacao("RF18", "índice")


def incluir_documento(
    config: Config, *, nome_arquivo: str, conteudo: bytes, metadados: dict, auditoria: Auditoria
) -> DocumentoAcervo:
    """RF20 — parte: índice.

    Esperado: guardrails.verificar_arquivo antes de gravar; arquivo novo em dados/acervo (nunca sobrescreve);
    entrada nova no manifesto com id, título, versão e tema validados por DocumentoAcervo; evento na auditoria.
    """
    raise PendenteDeImplementacao("RF20", "índice")


def excluir_documento(config: Config, documento_id: str, *, indice: IndiceVetorial, auditoria: Auditoria) -> dict:
    """RF24 — parte: índice.

    Esperado: remove os trechos de todas as coleções (indice.excluir), a entrada do manifesto e o arquivo do
    acervo; minutas já geradas com o documento ficam como registro histórico e a exclusão diz quantas citam
    o documento. Evento na auditoria com o id, sem o conteúdo. Devolve o que foi removido.
    """
    raise PendenteDeImplementacao("RF24", "índice")
