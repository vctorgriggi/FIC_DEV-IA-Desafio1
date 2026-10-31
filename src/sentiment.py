"""Classificação de sentimentos das avaliações de atendimento (RF22)."""

from __future__ import annotations

import json

from .config import Config
from .entradas import ArquivoInvalido
from .llm_client import ClienteLLM
from .schemas import AvaliacaoSentimento
from .tipos import PendenteDeImplementacao, Resultado

ARQUIVO_AVALIACOES = "avaliacoes.json"


def ler_avaliacoes(config: Config) -> list[dict]:
    """Avaliações de dados/avaliacoes/avaliacoes.json como [{"id", "texto"}], com ids únicos e texto não vazio."""
    caminho = config.caminho("avaliacoes") / ARQUIVO_AVALIACOES
    if not caminho.is_file():
        return []
    try:
        avaliacoes = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ArquivoInvalido(f"{config.relativo(caminho)} não é JSON válido ({erro}).") from None
    if not isinstance(avaliacoes, list) or not all(
        isinstance(a, dict) and isinstance(a.get("id"), str) and isinstance(a.get("texto"), str) and a["texto"].strip()
        for a in avaliacoes
    ):
        raise ArquivoInvalido(f"{config.relativo(caminho)} precisa ser uma lista de {{\"id\", \"texto\"}} preenchidos.")
    ids = [a["id"] for a in avaliacoes]
    if len(ids) != len(set(ids)):
        raise ArquivoInvalido(f"{config.relativo(caminho)} tem id de avaliação repetido.")
    return avaliacoes


def classificar(
    id_avaliacao: str, texto: str, *, cliente: ClienteLLM, config: Config, perfil: str | None = None
) -> Resultado[AvaliacaoSentimento]:
    """RF22 — parte: sentimentos.

    Esperado:
    - texto da avaliação dentro de prompts.delimitar, separado das instruções; saída restrita por
      llm_client.formato_json(AvaliacaoSentimento.model_json_schema(), "sentimento"), modelo do perfil;
    - polaridade em config["sentimentos"]["polaridades"]; mista, irônica ou sem contexto vira "indeterminada"
      ou pede revisão, segundo regra escrita no prompt e na documentação;
    - justificativa curta sobre o texto, nunca sobre a pessoa (sem personalidade, diagnóstico ou traço sensível).
    """
    raise PendenteDeImplementacao("RF22", "sentimentos")


def classificar_lote(
    avaliacoes: list[dict], *, cliente: ClienteLLM, config: Config, perfil: str | None = None
) -> list[Resultado[AvaliacaoSentimento]]:
    """RF22 — parte: sentimentos.

    Esperado: `classificar` para cada avaliação de ler_avaliacoes; falha de uma avaliação fica registrada e não
    interrompe as outras; o laço mora aqui, não na interface.
    """
    raise PendenteDeImplementacao("RF22", "sentimentos")
