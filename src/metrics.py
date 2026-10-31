"""Métricas determinísticas (RF18, RF22, RF23): contagem por código, com numerador e denominador visíveis."""

from __future__ import annotations

from .schemas import AvaliacaoSentimento
from .tipos import PendenteDeImplementacao


def proporcao(numerador: int, denominador: int) -> dict:
    """Taxa com os dois termos; denominador zero dá valor None em vez de divisão por zero (T13)."""
    if numerador < 0 or denominador < 0 or numerador > denominador:
        raise ValueError(f"Proporção inválida: {numerador}/{denominador}.")
    return {
        "numerador": numerador,
        "denominador": denominador,
        "valor": round(numerador / denominador, 3) if denominador else None,
    }


def agregar_sentimentos(avaliacoes: list[AvaliacaoSentimento], *, polaridades: list[str] | None = None) -> dict:
    """RF22/RF23 — parte: sentimentos.

    Esperado: total e proporção por polaridade (com proporcao), contagem de "necessita_revisao", filtro opcional
    por polaridade, ids repetidos contados uma vez e registrados, conjunto vazio sem erro (T13). Não usa
    confianca_declarada em nenhuma conta.
    """
    raise PendenteDeImplementacao("RF22", "sentimentos")
