"""Resultado esperado contra obtido em cada caso (RF13), a partir dos gabaritos.

Campos com valor exato (protocolo, data, solicitante, categoria) são conferidos
automaticamente; assunto e pedido são texto livre e ficam lado a lado para o
julgamento humano. A minuta é conferida contra minuta_deve_conter e
minuta_nao_pode_conter.
"""

from __future__ import annotations

import json

from .comparacao import tokens
from .config import Config

CAMPOS_EXATOS = ("protocolo", "data", "solicitante", "categoria")
CAMPOS_LIVRES = ("assunto", "pedido")


def _normal(texto: object) -> str:
    return " ".join(tokens(str(texto)))


def avaliar_minuta(metadados: dict, config: Config) -> dict | None:
    """Avaliação de uma minuta; None se o caso não tem gabarito."""
    caminho_gabarito = config.raiz / config.caso(metadados["caso_id"])["gabarito"]
    if not caminho_gabarito.is_file():
        return None
    gabarito = json.loads(caminho_gabarito.read_text(encoding="utf-8"))
    obtidos = json.loads((config.raiz / metadados["extracao"]).read_text(encoding="utf-8"))["campos"]
    minuta = _normal((config.raiz / metadados["arquivo_minuta"]).read_text(encoding="utf-8"))
    esperados = gabarito.get("campos_esperados", {})

    campos = {
        campo: {"esperado": esperados[campo], "obtido": obtidos.get(campo), "confere": _normal(esperados[campo]) == _normal(obtidos.get(campo, ""))}
        for campo in CAMPOS_EXATOS
        if esperados.get(campo)
    }
    campos.update(
        {campo: {"esperado": esperados[campo], "obtido": obtidos.get(campo), "confere": None} for campo in CAMPOS_LIVRES if esperados.get(campo)}
    )
    ausentes_esperados = sorted(gabarito.get("campos_ausentes_esperados", []))
    ausentes_obtidos = sorted(obtidos.get("campos_ausentes", []))
    deve_conter = {item: _normal(item) in minuta for item in gabarito.get("minuta_deve_conter", [])}
    nao_pode_conter = {item: _normal(item) in minuta for item in gabarito.get("minuta_nao_pode_conter", [])}

    falhas = [f"campo {c}: esperado {v['esperado']!r}, obtido {v['obtido']!r}" for c, v in campos.items() if v["confere"] is False]
    if ausentes_esperados != ausentes_obtidos:
        falhas.append(f"campos ausentes: esperado {ausentes_esperados}, obtido {ausentes_obtidos}")
    falhas += [f"minuta não contém {item!r}" for item, achou in deve_conter.items() if not achou]
    falhas += [f"minuta contém {item!r}" for item, achou in nao_pode_conter.items() if achou]
    return {
        "id_execucao": metadados["id_execucao"],
        "caso_id": metadados["caso_id"],
        "status_revisao": metadados["status"],
        "campos": campos,
        "campos_ausentes": {"esperado": ausentes_esperados, "obtido": ausentes_obtidos},
        "minuta_deve_conter": deve_conter,
        "minuta_nao_pode_conter": nao_pode_conter,
        "falhas": falhas,
    }


def avaliar_todas(config: Config) -> list[dict]:
    avaliacoes = []
    for caminho in sorted(config.caminho("minutas").glob("*.json")):
        avaliacao = avaliar_minuta(json.loads(caminho.read_text(encoding="utf-8")), config)
        if avaliacao is not None:
            avaliacoes.append(avaliacao)
    return avaliacoes
