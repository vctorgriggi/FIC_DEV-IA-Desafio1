"""Geração da minuta institucional (RF09)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .llm_client import ClienteLLM, RespostaLLM
from .prompts import Prompt
from .tipos import PendenteDeImplementacao


@dataclass
class Minuta:
    texto: str
    campos_ausentes: list[str]
    fontes: list[str]
    resposta: RespostaLLM | None = None
    prompt: Prompt | None = None
    # Caminho do arquivo final, se a minuta for renderizada (ex.: HTML/PDF com o brasão).
    arquivo_renderizado: str | None = None
    metadados: dict = field(default_factory=dict)


def gerar_minuta(campos: dict, *, fontes: list[str], cliente: ClienteLLM, config: Config) -> Minuta:
    """RF09 — parte: texto.

    Esperado:
    - usar só `campos` (saída de extracao.normalizar_extracao) e o contexto fornecido;
    - seguir o modelo institucional definido pela equipe, com a imagem institucional
      de config.dados["imagem_institucional"] na saída (seção 6 do enunciado);
    - marcar explicitamente cada campo com valor extracao.NAO_LOCALIZADO;
    - listar `fontes` (arquivos de origem) no texto da minuta.
    Não existe envio: a minuta termina em revisão humana (revisao.py).
    """
    raise PendenteDeImplementacao("RF09", "texto")
