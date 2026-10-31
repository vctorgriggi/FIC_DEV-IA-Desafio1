"""Geração fundamentada no acervo (RF19): resposta ou minuta com citações, abstenção ou conflito."""

from __future__ import annotations

from .config import Config
from .embeddings import IndiceVetorial
from .llm_client import ClienteLLM
from .schemas import RespostaRAG, SolicitacaoEstruturada
from .tipos import PendenteDeImplementacao, Resultado


def responder(
    pergunta: str,
    *,
    indice: IndiceVetorial,
    cliente: ClienteLLM,
    config: Config,
    perfil: str | None = None,
) -> Resultado[RespostaRAG]:
    """RF19 — parte: RAG.

    Esperado:
    - consulta mascarada (privacidade.mascarar) antes de ir ao embedding e ao modelo (RF24, minimização);
    - mandar ao modelo só os trechos recuperados, cada um dentro de prompts.delimitar com o id do trecho;
    - saída restrita por schemas.RespostaGerada, com modelo de config.perfil_geracao(perfil) e prompt versionado;
    - status "sem_evidencia" quando nenhum trecho sustenta a resposta, sem texto institucional inventado;
    - status "conflito" quando trechos divergem sem vigência ou prioridade que resolva (DocumentoAcervo.substitui);
    - cada afirmação cita ids de trechos que estão em `trechos`.
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
) -> Resultado[RespostaRAG]:
    """RF19 — parte: RAG.

    Esperado:
    - consulta montada da solicitação (assunto e pedido), mascarada antes de sair da máquina;
    - fatos do caso só da solicitação; orientações institucionais só do acervo; os dois em blocos delimitados separados;
    - a mesma regra de status e de citação por afirmação de `responder`; sem evidência, a minuta diz o que falta;
    - o texto vai para revisão humana (estado "pendente"), nunca para envio.
    """
    raise PendenteDeImplementacao("RF19", "RAG")
