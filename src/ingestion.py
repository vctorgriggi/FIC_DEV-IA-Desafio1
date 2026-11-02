"""Ingestão do acervo (RF17, RF18): manifesto, extração de texto e divisão em trechos.

O manifesto (dados/acervo/acervo.json) é o contrato entre quem escreve o
acervo e quem o indexa: cada documento tem id, título, versão e arquivo.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from . import guardrails
from .audit import Auditoria, Evento, novo_id
from .config import Config
from .entradas import ArquivoInvalido
from .revisao import hash_arquivo
from .schemas import DocumentoAcervo, Trecho

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


# Título de seção dos documentos do acervo: linha que começa com "1." ou "2.3".
_SECAO = re.compile(r"^\d+(?:\.\d+)*\.?\s+\S.*$", re.MULTILINE)


def extrair_texto(documento: DocumentoAcervo, *, config: Config) -> list[tuple[int | None, str]]:
    """TXT vira um bloco com página None; PDF textual, um bloco por página com texto, numerada a partir de 1."""
    arquivo = caminho_documento(config, documento)
    limite_mb = config.dados["acervo"]["tamanho_max_mb"]
    if arquivo.stat().st_size > limite_mb * 1024 * 1024:
        raise ArquivoInvalido(f"Documento {documento.id} passa de {limite_mb} MB (acervo.tamanho_max_mb).")
    extensao = arquivo.suffix.lower()
    if extensao == ".txt":
        try:
            texto = arquivo.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ArquivoInvalido(f"Documento {documento.id} não está em UTF-8.") from None
        if not texto.strip():
            raise ArquivoInvalido(f"Documento {documento.id} está vazio.")
        return [(None, texto)]
    if extensao == ".pdf":
        try:
            paginas = [(numero, pagina.extract_text() or "") for numero, pagina in enumerate(PdfReader(arquivo).pages, 1)]
        except (PdfReadError, ValueError) as erro:
            raise ArquivoInvalido(f"Documento {documento.id}: PDF ilegível ({type(erro).__name__}).") from None
        com_texto = [(numero, texto) for numero, texto in paginas if texto.strip()]
        if not com_texto:
            raise ArquivoInvalido(f"Documento {documento.id}: PDF sem texto extraível (digitalizado?); use OCR antes de indexar.")
        return com_texto
    raise ArquivoInvalido(f"Documento {documento.id}: extensão {extensao} sem extrator.")


def dividir(documento: DocumentoAcervo, paginas: list[tuple[int | None, str]], *, perfil: str, config: Config) -> list[Trecho]:
    """Janelas de `tamanho` caracteres com `sobreposicao`, por página; ids determinísticos pelo hash do arquivo.

    Mesmo arquivo dá os mesmos ids (reindexar não duplica); arquivo mudado dá ids novos.
    A seção é o título vigente no início da janela e os que começam dentro dela.
    """
    parametros = config.dados["indice"]["chunking"][perfil]
    if parametros["unidade"] != "caracteres":
        raise ValueError(f"Chunking {perfil}: unidade '{parametros['unidade']}' não suportada; use caracteres.")
    tamanho, sobreposicao = parametros["tamanho"], parametros["sobreposicao"]
    if not 0 <= sobreposicao < tamanho:
        raise ValueError(f"Chunking {perfil}: sobreposição precisa ficar entre 0 e o tamanho.")
    hash_documento = hash_arquivo(caminho_documento(config, documento))
    trechos: list[Trecho] = []
    for pagina, texto in paginas:
        titulos = [(m.start(), m.group().strip()) for m in _SECAO.finditer(texto)]
        for inicio, fim in _janelas(texto, tamanho, sobreposicao):
            conteudo = texto[inicio:fim].strip()
            if not conteudo:
                continue
            anteriores = [titulo for posicao, titulo in titulos if posicao <= inicio]
            internos = [titulo for posicao, titulo in titulos if inicio < posicao < fim]
            secoes = anteriores[-1:] + internos
            trechos.append(
                Trecho(
                    id=f"{documento.id}:{hash_documento[:12]}:{perfil}:{len(trechos)}",
                    documento_id=documento.id,
                    titulo=documento.titulo,
                    versao=documento.versao,
                    hash_documento=hash_documento,
                    chunking=perfil,
                    texto=conteudo,
                    pagina=pagina,
                    secao=" / ".join(secoes) or None,
                )
            )
    return trechos


def _janelas(texto: str, tamanho: int, sobreposicao: int) -> list[tuple[int, int]]:
    """Posições [início, fim) das janelas; o corte recua até um espaço para não partir palavra ao meio."""
    janelas: list[tuple[int, int]] = []
    inicio = 0
    while inicio < len(texto):
        fim = min(inicio + tamanho, len(texto))
        if fim < len(texto):
            espaco = max(texto.rfind(" ", inicio, fim), texto.rfind("\n", inicio, fim))
            # Só recua se sobrar mais que a sobreposição; senão a janela seguinte não avançaria.
            if espaco - inicio > sobreposicao:
                fim = espaco
        janelas.append((inicio, fim))
        if fim >= len(texto):
            break
        inicio = fim - sobreposicao
    return janelas


def incluir_documento(
    config: Config, *, nome_arquivo: str, conteudo: bytes, metadados: dict, auditoria: Auditoria
) -> DocumentoAcervo:
    """Grava um documento novo no acervo e no manifesto, depois do guardrail de arquivo; nunca sobrescreve.

    Texto não extraível desfaz a inclusão: documento que não se indexa não entra no manifesto.
    """
    decisao = guardrails.verificar_arquivo(nome_arquivo, len(conteudo), config=config)
    if decisao.decisao != "permitir":
        raise ArquivoInvalido(f"Arquivo não incluído ({decisao.regra}): {decisao.motivo}")
    nome = Path(nome_arquivo).name
    if not re.fullmatch(r"[\w.-]+", nome) or nome.startswith("."):
        raise ArquivoInvalido("Nome de arquivo aceita só letras, números, ponto, hífen e sublinhado.")
    preenchidos = {chave: valor.strip() if isinstance(valor, str) else valor for chave, valor in metadados.items()}
    preenchidos = {chave: valor for chave, valor in preenchidos.items() if valor not in ("", None, [])}
    faltando = [campo for campo in ("id", "titulo", "versao", "tema") if campo not in preenchidos]
    if faltando:
        raise ArquivoInvalido(f"Preencha {', '.join(faltando)} para incluir o documento.")
    try:
        documento = DocumentoAcervo(**{**preenchidos, "arquivo": nome})
    except ValidationError as erro:
        raise ArquivoInvalido(f"Metadados do documento inválidos: {erro.error_count()} erro(s).") from None
    if documento.id in {d.id for d in ler_manifesto(config)}:
        raise ArquivoInvalido(f"Já existe documento com id {documento.id}; versão nova pede id novo e `substitui`.")
    destino = caminho_documento(config, documento)
    if destino.exists():
        raise ArquivoInvalido(f"Já existe {nome} no acervo; o arquivo original não é sobrescrito.")
    anteriores = _manifesto_bruto(config)["documentos"]
    destino.write_bytes(conteudo)
    try:
        extrair_texto(documento, config=config)
        _gravar_manifesto(config, [*anteriores, documento.model_dump(mode="json")])
        ler_manifesto(config)
    except ArquivoInvalido:
        _gravar_manifesto(config, anteriores)
        destino.unlink()
        raise
    auditoria.registrar(
        Evento(
            id_execucao=novo_id(), caso_id=documento.id, etapa="acervo_inclusao", arquivo_origem=config.relativo(destino),
            extra={"versao": documento.versao, "hash": hash_arquivo(destino), "tamanho_bytes": len(conteudo)},
        )
    )
    return documento


def excluir_documento(config: Config, documento_id: str, *, indice: IndiceVetorial, auditoria: Auditoria) -> dict:
    """Remove trechos (todas as coleções), entrada do manifesto e arquivo; minutas já geradas ficam como histórico.

    Documento que outro `substitui` não sai: o manifesto ficaria inválido e o conflito de fontes (T10), sem regra.
    """
    documentos = ler_manifesto(config)
    alvo = next((d for d in documentos if d.id == documento_id), None)
    if alvo is None:
        raise ArquivoInvalido(f"Documento {documento_id} não está no manifesto.")
    dependentes = [d.id for d in documentos if documento_id in d.substitui]
    if dependentes:
        raise ArquivoInvalido(f"{', '.join(dependentes)} substitui {documento_id}; ajuste `substitui` antes de excluir.")
    arquivo = caminho_documento(config, alvo)
    trechos_removidos = indice.excluir(documento_id)
    _gravar_manifesto(config, [d for d in _manifesto_bruto(config)["documentos"] if d["id"] != documento_id])
    arquivo.unlink(missing_ok=True)
    removido = {
        "documento_id": documento_id,
        "versao": alvo.versao,
        "arquivo": config.relativo(arquivo),
        "trechos_removidos": trechos_removidos,
        "minutas_que_citam": _minutas_que_citam(config, documento_id),
    }
    auditoria.registrar(
        Evento(id_execucao=novo_id(), caso_id=documento_id, etapa="acervo_exclusao", arquivo_origem=removido["arquivo"], extra=removido)
    )
    return removido


def _manifesto_bruto(config: Config) -> dict:
    return json.loads((config.raiz / config.dados["acervo"]["manifesto"]).read_text(encoding="utf-8"))


def _gravar_manifesto(config: Config, documentos: list[dict]) -> None:
    caminho = config.raiz / config.dados["acervo"]["manifesto"]
    bruto = {**_manifesto_bruto(config), "documentos": documentos}
    caminho.write_text(json.dumps(bruto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _minutas_que_citam(config: Config, documento_id: str) -> int:
    total = 0
    for caminho in config.caminho("minutas_rag").glob("*.json"):
        resposta = json.loads(caminho.read_text(encoding="utf-8")).get("resposta") or {}
        if any(t["trecho"]["documento_id"] == documento_id for t in resposta.get("trechos", [])):
            total += 1
    return total
