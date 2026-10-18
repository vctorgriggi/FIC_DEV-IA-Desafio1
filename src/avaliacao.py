"""Resultado esperado contra obtido em cada caso (RF13), a partir dos gabaritos.

Campos com valor exato (protocolo, data, solicitante, categoria) são conferidos
automaticamente; assunto e pedido são texto livre e ficam lado a lado para o
julgamento humano. A minuta é conferida contra minuta_deve_conter e
minuta_nao_pode_conter.
"""

from __future__ import annotations

import json
import re

from .comparacao import tokens
from .config import Config
from .revisao import AGUARDANDO, STATUS_APROVADOS

CAMPOS_EXATOS = ("protocolo", "data", "solicitante", "categoria")
CAMPOS_LIVRES = ("assunto", "pedido")


MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
_DATA_EXTENSO = re.compile(r"^(\d{1,2})º? de (" + "|".join(MESES) + r") de (\d{4})$")


def _normal(texto: object) -> str:
    return " ".join(tokens(str(texto)))


def data_canonica(valor: str) -> str:
    """Data falada ("14 de outubro de 2026") e numérica ("14/10/2026") são o mesmo dado."""
    achado = _DATA_EXTENSO.match(valor.strip().casefold())
    if not achado:
        return valor.strip()
    dia, mes, ano = achado.groups()
    return f"{int(dia):02d}/{MESES.index(mes) + 1:02d}/{ano}"


def _confere(campo: str, esperado: object, obtido: object) -> bool:
    if campo == "data":
        return data_canonica(str(esperado)) == data_canonica(str(obtido))
    return _normal(esperado) == _normal(obtido)


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
        campo: {"esperado": esperados[campo], "obtido": obtidos.get(campo), "confere": _confere(campo, esperados[campo], obtidos.get(campo, ""))}
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


def taxa_por_caso(config: Config) -> dict:
    """RF13 pede a taxa "dos casos": vale a decisão mais recente de cada caso, não cada minuta."""
    finais: dict[str, tuple[str, str]] = {}
    for caminho in config.caminho("minutas").glob("*.json"):
        meta = json.loads(caminho.read_text(encoding="utf-8"))
        if meta["status"] == AGUARDANDO:
            continue
        quando = meta["revisao"]["data_hora"]
        if meta["caso_id"] not in finais or quando > finais[meta["caso_id"]][0]:
            finais[meta["caso_id"]] = (quando, meta["status"])
    decisao = {caso: status for caso, (_, status) in sorted(finais.items())}
    aprovados = sum(status in STATUS_APROVADOS for status in decisao.values())
    return {
        "decisao_final": decisao,
        "aprovados": aprovados,
        "casos_revisados": len(decisao),
        "taxa": round(aprovados / len(decisao), 3) if decisao else None,
    }
