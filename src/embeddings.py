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
    """RF17 — parte: índice.

    Esperado:
    - chromadb.PersistentClient em config.caminho("indice"); uma coleção por perfil de chunking
      (f"{config.dados['indice']['colecao']}_{perfil}"), com espaço de cosseno;
    - metadados da coleção com modelo e dimensão do embedding; abrir com modelo diferente é erro que pede reindexação;
    - upsert pelo id do Trecho, para reindexar sem duplicar;
    - excluir por documento_id remove todos os trechos do documento (RF24).
    """

    def __init__(self, config: Config, cliente: ClienteLLM, *, perfil: str | None = None):
        self.config = config
        self.cliente = cliente
        self.perfil = perfil or config.dados["indice"]["chunking_ativo"]

    def indexar(self, documento: DocumentoAcervo) -> int:
        """Extrai, divide e grava os trechos do documento; devolve quantos trechos ficaram no índice."""
        raise PendenteDeImplementacao("RF17", "índice")

    def buscar(self, consulta: str, *, top_k: int | None = None) -> list[TrechoRecuperado]:
        """Top-k por distância de cosseno (top_k padrão em config["indice"]["top_k"])."""
        raise PendenteDeImplementacao("RF17", "índice")

    def excluir(self, documento_id: str) -> int:
        """Remove os trechos do documento; devolve quantos saíram. A exclusão vai para a auditoria."""
        raise PendenteDeImplementacao("RF24", "índice")

    def contar(self) -> int:
        raise PendenteDeImplementacao("RF17", "índice")

    def info(self) -> dict:
        """Modelo e dimensão do embedding, perfil de chunking, total de trechos e documentos indexados."""
        raise PendenteDeImplementacao("RF17", "índice")
