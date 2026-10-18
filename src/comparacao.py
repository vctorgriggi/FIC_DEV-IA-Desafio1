"""Comparação de texto extraído com o gabarito (RF06 e RF08: acertos e erros)."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# Pontuação que faz parte de dado (data, CPF, e-mail, protocolo) fica no token.
_FORA_DO_TOKEN = re.compile(r"[^a-z0-9./@-]+")


def tokens(texto: str) -> list[str]:
    """Palavras comparáveis: sem caixa nem acento, com a pontuação de dados preservada.

    Acento e caixa saem porque formulário manuscrito costuma vir em maiúsculas
    sem acento; a métrica mede leitura, não ortografia.
    """
    sem_acento = unicodedata.normalize("NFKD", texto.casefold())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return [t.strip(".-") for t in _FORA_DO_TOKEN.sub(" ", sem_acento).split() if t.strip(".-")]


def comparar_texto(obtido: str, referencia: str) -> dict:
    esperado, lido = tokens(referencia), tokens(obtido)
    comparador = SequenceMatcher(None, esperado, lido, autojunk=False)
    corretas = sum(bloco.size for bloco in comparador.get_matching_blocks())
    tipos = {"replace": "substituicao", "delete": "omissao", "insert": "insercao"}
    erros = [
        {"tipo": tipos[op], "esperado": " ".join(esperado[i1:i2]), "obtido": " ".join(lido[j1:j2])}
        for op, i1, i2, j1, j2 in comparador.get_opcodes()
        if op != "equal"
    ]
    return {
        "similaridade": round(comparador.ratio(), 3),
        "palavras_referencia": len(esperado),
        "palavras_corretas": corretas,
        "taxa_acerto_palavras": round(corretas / len(esperado), 3) if esperado else None,
        "erros": erros,
    }


def conferir_dados_criticos(obtido: str, dados_criticos: list[str]) -> dict:
    texto = f" {' '.join(tokens(obtido))} "
    encontrados, ausentes = [], []
    for valor in dados_criticos:
        (encontrados if f" {' '.join(tokens(valor))} " in texto else ausentes).append(valor)
    return {"encontrados": encontrados, "nao_encontrados": ausentes}


def comparar_com_gabarito(texto_bruto: str, texto_revisado: str, gabarito: dict) -> dict | None:
    """Compara as duas versões com o texto de referência; None se o gabarito não tem referência."""
    referencia = (gabarito.get("texto_referencia") or "").strip()
    if not referencia:
        return None
    criticos = gabarito.get("dados_criticos") or []
    return {
        "bruto": comparar_texto(texto_bruto, referencia),
        "revisado": comparar_texto(texto_revisado, referencia),
        "dados_criticos": conferir_dados_criticos(texto_revisado, criticos),
    }
