"""Métricas determinísticas (RF15, RF18, RF22, RF23): contagem por código, com numerador e denominador visíveis.

Uma função por parte, já reservada aqui, para que cada estudante preencha a sua sem conflito de merge.
"""

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


def acuracia_categorias(obtidas: dict[str, str | None], esperadas: dict[str, str]) -> dict:
    """RF15/RF23 — parte: NLP.

    Esperado: por id de solicitação, categoria obtida contra a do gabarito; proporção de acertos sobre as
    solicitações com gabarito e a lista das divergências. Sem gabarito, a solicitação não entra no denominador.
    """
    raise PendenteDeImplementacao("RF15", "NLP")


def acerto_recuperacao(recuperados: dict[str, list[str]], referencias: dict[str, list[str]]) -> dict:
    """RF18/RF23 — parte: índice.

    Esperado: pergunta conta como acerto se ao menos um id de trecho de referência está no top-k recuperado;
    proporção sobre as perguntas respondíveis (cinco), com o resultado de cada pergunta.
    """
    raise PendenteDeImplementacao("RF18", "índice")


def agregar_sentimentos(avaliacoes: list[AvaliacaoSentimento], *, polaridades: list[str] | None = None) -> dict:
    """RF22/RF23 — parte: sentimentos.

    Esperado: total e proporção por polaridade (com proporcao), contagem de "necessita_revisao", filtro opcional
    por polaridade, ids repetidos contados uma vez e registrados, conjunto vazio sem erro (T13). Não usa
    confianca_declarada em nenhuma conta.
    """
    raise PendenteDeImplementacao("RF22", "sentimentos")
