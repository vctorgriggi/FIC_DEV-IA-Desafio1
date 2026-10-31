"""Classificação de sentimentos das avaliações de atendimento (RF22)."""

from __future__ import annotations

from .config import Config
from .llm_client import ClienteLLM
from .schemas import AvaliacaoSentimento
from .tipos import PendenteDeImplementacao


def classificar(id_avaliacao: str, texto: str, *, cliente: ClienteLLM, config: Config) -> AvaliacaoSentimento:
    """RF22 — parte: sentimentos.

    Esperado:
    - texto da avaliação dentro de prompts.delimitar, separado das instruções; saída restrita por esquema;
    - polaridade em config["sentimentos"]["polaridades"]; mista, irônica ou sem contexto vira "indeterminada"
      ou pede revisão, segundo regra escrita no prompt e na documentação;
    - justificativa curta sobre o texto, nunca sobre a pessoa (sem personalidade, diagnóstico ou traço sensível).
    """
    raise PendenteDeImplementacao("RF22", "sentimentos")
