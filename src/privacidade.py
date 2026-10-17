"""Minimização de dados (RF12) e ocultação de segredos em logs (RF04, RF11)."""

from __future__ import annotations

import re

MARCADOR = "[{tipo} removido]"

PADROES_PESSOAIS = {
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "rg": re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dXx]\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    "telefone": re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-\d{4}\b"),
}

# Formato das chaves do Google AI Studio; cobre a chave que não veio do .env.
PADRAO_CHAVE_GOOGLE = re.compile(r"AIza[0-9A-Za-z_\-]{35}")


def mascarar(texto: str, tipos: list[str]) -> tuple[str, dict[str, int]]:
    """Troca dados pessoais por marcadores antes de enviar ao provedor.

    Devolve o texto mascarado e quantas ocorrências de cada tipo foram trocadas.
    O texto original continua só na máquina local.
    """
    contagem: dict[str, int] = {}
    for tipo in tipos:
        texto, total = PADROES_PESSOAIS[tipo].subn(MARCADOR.format(tipo=tipo.upper()), texto)
        if total:
            contagem[tipo] = total
    return texto, contagem


def ocultar_segredos(texto: str, segredos: list[str]) -> str:
    for segredo in segredos:
        if segredo:
            texto = texto.replace(segredo, "[SEGREDO OCULTADO]")
    return PADRAO_CHAVE_GOOGLE.sub("[SEGREDO OCULTADO]", texto)
