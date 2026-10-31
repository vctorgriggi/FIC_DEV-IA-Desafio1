"""Índice vetorial persistente do acervo (RF17, RF24), sobre o Chroma.

Os vetores vêm de ClienteLLM.gerar_embeddings com config["modelos"]["embeddings"];
trocar esse modelo exige reindexar. Trocar o perfil de geração não toca o índice (RF21).
"""

from __future__ import annotations

from .config import Config
from .llm_client import ClienteLLM
from .schemas import DocumentoAcervo, TrechoRecuperado
from .tipos import PendenteDeImplementacao


class IndiceVetorial:
    """RF17 — parte: índice. `chunking` é uma chave de config["indice"]["chunking"] (A ou B), não o perfil de geração.

    Esperado:
    - chromadb.PersistentClient em config.caminho("indice"); uma coleção por chunking
      (f"{config.dados['indice']['colecao']}_{chunking}"), com espaço de cosseno;
    - metadados da coleção com modelo e dimensão do embedding; abrir com modelo diferente é erro que pede reindexação;
    - upsert pelo id do Trecho; se o hash do documento mudou, apagar antes os trechos antigos do mesmo documento_id,
      para que versão nova ou arquivo editado não deixe trecho órfão (T06);
    - metadado None não é gravado pelo Chroma: pagina e secao voltam ausentes, e Trecho os aceita assim.
    """

    def __init__(self, config: Config, cliente: ClienteLLM, *, chunking: str | None = None):
        chunking = chunking or config.dados["indice"]["chunking_ativo"]
        if chunking not in config.dados["indice"]["chunking"]:
            raise KeyError(f"Chunking '{chunking}' não existe. Opções: {', '.join(config.dados['indice']['chunking'])}.")
        self.config = config
        self.cliente = cliente
        self.chunking = chunking

    def indexar(self, documento: DocumentoAcervo) -> int:
        """Extrai, divide e grava os trechos do documento; devolve quantos trechos dele ficaram no índice."""
        raise PendenteDeImplementacao("RF17", "índice")

    def buscar(self, consulta: str, *, top_k: int | None = None) -> list[TrechoRecuperado]:
        """Top-k por distância de cosseno (top_k padrão em config["indice"]["top_k"]); a consulta chega mascarada."""
        raise PendenteDeImplementacao("RF17", "índice")

    def excluir(self, documento_id: str) -> int:
        """Remove os trechos do documento de todas as coleções de chunking; devolve quantos saíram."""
        raise PendenteDeImplementacao("RF24", "índice")

    def contar(self) -> int:
        raise PendenteDeImplementacao("RF17", "índice")

    def info(self) -> dict:
        """Modelo e dimensão do embedding, chunking, total de trechos e {documento_id: {versao, hash}} indexados."""
        raise PendenteDeImplementacao("RF17", "índice")

    def desatualizados(self, documentos: list[DocumentoAcervo]) -> list[str]:
        """Ids do manifesto ausentes do índice ou com versão ou hash diferentes do arquivo atual (RF20)."""
        raise PendenteDeImplementacao("RF17", "índice")
