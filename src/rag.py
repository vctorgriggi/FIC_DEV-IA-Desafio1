"""Geração fundamentada no acervo (RF19): resposta ou minuta com citações, abstenção ou conflito."""

from __future__ import annotations

from .config import Config
from .embeddings import IndiceVetorial
from .llm_client import ClienteLLM
from .schemas import RespostaRAG, SolicitacaoEstruturada
from .tipos import PendenteDeImplementacao


def responder(
    pergunta: str,
    *,
    indice: IndiceVetorial,
    cliente: ClienteLLM,
    config: Config,
    perfil: str | None = None,
) -> RespostaRAG:
    """RF19 — parte: RAG.

    Esperado:
    - buscar no índice e mandar ao modelo só os trechos recuperados, cada um dentro de prompts.delimitar com o id do trecho;
    - modelo pelo perfil de geração (config.perfil_geracao(perfil)); prompt versionado em prompts/;
    - status "sem_evidencia" quando nenhum trecho sustenta a resposta, sem texto institucional inventado;
    - status "conflito" quando trechos divergem sem vigência ou prioridade que resolva (DocumentoAcervo.substitui);
    - toda afirmação institucional cita ids de trechos que estão em `trechos`.
    """
    raise PendenteDeImplementacao("RF19", "RAG")


def minuta_fundamentada(
    solicitacao: SolicitacaoEstruturada,
    texto_original: str,
    *,
    indice: IndiceVetorial,
    cliente: ClienteLLM,
    config: Config,
    perfil: str | None = None,
) -> RespostaRAG:
    """RF19 — parte: RAG.

    Esperado:
    - fatos do caso só da solicitação; orientações institucionais só do acervo; os dois em blocos delimitados separados;
    - a mesma regra de status de `responder`; sem evidência, a minuta diz o que falta e pede revisão;
    - o texto vai para revisão humana (estado "pendente"), nunca para envio.
    """
    raise PendenteDeImplementacao("RF19", "RAG")
