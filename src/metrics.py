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
    divergencias = [
        {"id": identificador, "esperada": esperada, "obtida": obtidas.get(identificador)}
        for identificador, esperada in sorted(esperadas.items())
        if identificador not in obtidas or obtidas.get(identificador) != esperada
    ]
    denominador = len(esperadas)
    numerador = denominador - len(divergencias)
    return {
        **proporcao(numerador, denominador),
        "percentual": round(100 * numerador / denominador, 2) if denominador else None,
        "divergencias": divergencias,
    }


def acerto_recuperacao(recuperados: dict[str, list[str]], referencias: dict[str, list[str]]) -> dict:
    """RF18/RF23 — parte: índice.

    Esperado: pergunta conta como acerto se ao menos um id de trecho de referência está no top-k recuperado;
    proporção sobre as perguntas respondíveis (cinco), com o resultado de cada pergunta.
    """
    por_pergunta = []
    for pergunta, esperados in sorted(referencias.items()):
        obtidos = recuperados.get(pergunta, [])
        encontrados = [identificador for identificador in obtidos if identificador in esperados]
        por_pergunta.append({"id": pergunta, "acerto": bool(encontrados), "referencias_no_top_k": encontrados,
                             "recuperados": list(obtidos)})
    return {
        **proporcao(sum(p["acerto"] for p in por_pergunta), len(por_pergunta)),
        "por_pergunta": por_pergunta,
    }


def agregar_sentimentos(avaliacoes: list[AvaliacaoSentimento], *, polaridades: list[str] | None = None) -> dict:
    """RF22/RF23 — parte: sentimentos.

    Esperado: total e proporção por polaridade (com proporcao), contagem de "necessita_revisao", filtro opcional
    por polaridade, ids repetidos contados uma vez e registrados, conjunto vazio sem erro (T13). Não usa
    confianca_declarada em nenhuma conta.
    """
    rotulos = ['positiva', 'negativa', 'neutra', 'indeterminada']
    if polaridades is not None and set(polaridades) - set(rotulos):
        raise ValueError('Filtro contém polaridade inválida.')
    unicas = {}
    duplicados = set()
    for avaliacao in avaliacoes:
        if avaliacao.id in unicas:
            duplicados.add(avaliacao.id)
        else:
            unicas[avaliacao.id] = avaliacao
    filtradas = [a for a in unicas.values() if polaridades is None or a.polaridade in polaridades]
    total = len(filtradas)
    return {
        'total': total, 'total_sem_filtro': len(unicas), 'ids_repetidos': sorted(duplicados),
        'necessita_revisao': sum(a.necessita_revisao for a in filtradas),
        'por_polaridade': {p: proporcao(sum(a.polaridade == p for a in filtradas), total) for p in rotulos},
    }


def conferir_sentimentos(avaliacoes: list[AvaliacaoSentimento], esperadas: dict[str, str]) -> dict:
    """Conferência por ID contra gabarito prévio; faltantes contam como erro."""
    obtidas = {}
    for avaliacao in avaliacoes:
        obtidas.setdefault(avaliacao.id, avaliacao.polaridade)
    linhas = [{'id': id_, 'esperada': p, 'obtida': obtidas.get(id_),
               'acerto': obtidas.get(id_) == p} for id_, p in esperadas.items()]
    return {'acuracia': proporcao(sum(linha['acerto'] for linha in linhas), len(linhas)), 'avaliacoes': linhas}
