"""Tipos compartilhados entre as modalidades."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from .llm_client import RespostaLLM
from .prompts import Prompt


T = TypeVar("T")


class PendenteDeImplementacao(NotImplementedError):
    def __init__(self, requisito: str, parte: str):
        super().__init__(f"{requisito} ainda não implementado (parte: {parte}).")
        self.requisito = requisito
        self.parte = parte


@dataclass
class TextoExtraido:
    """Saída comum da transcrição (RF06) e do OCR/visão (RF08).

    O fluxo grava texto_bruto e texto_revisado em dados/processados/ e segue
    com texto_revisado para a extração de campos.
    """

    texto_bruto: str
    texto_revisado: str
    # Cada item no formato "trecho — motivo"; a confirmação humana destaca o campo que contém o trecho.
    trechos_incertos: list[str] = field(default_factory=list)
    # Ex.: idioma e duração do áudio (RF06), páginas do documento (RF08).
    metadados: dict = field(default_factory=dict)
    resposta: RespostaLLM | None = None
    prompt: Prompt | None = None


@dataclass
class Resultado(Generic[T]):
    """Saída de uma parte do Desafio 2 com o que a auditoria precisa (RF21).

    `respostas` traz tempo, tokens e custo de cada chamada (mais de uma quando houve
    a tentativa de correção do RF14); `prompt` dá versão e hash para o log.
    """

    valor: T
    respostas: list[RespostaLLM] = field(default_factory=list)
    prompt: Prompt | None = None
