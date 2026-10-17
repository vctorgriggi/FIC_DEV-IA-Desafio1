"""Prompts versionados (RF02, RF11) e delimitação de conteúdo não confiável (RF03)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .config import Config

ETIQUETA = "conteudo_externo"
_ETIQUETA_NO_CONTEUDO = re.compile(rf"<(/?)\s*{ETIQUETA}", re.IGNORECASE)


@dataclass(frozen=True)
class Prompt:
    nome: str
    versao: int
    texto: str

    @property
    def identificador(self) -> str:
        return f"{self.nome}_v{self.versao}"

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.texto.encode("utf-8")).hexdigest()[:12]


def carregar_prompt(config: Config, nome: str, versao: int) -> Prompt:
    """Lê prompts/<nome>_v<versao>.md. Prompt alterado é versão nova, nunca edição da antiga."""
    caminho = config.caminho("prompts") / f"{nome}_v{versao}.md"
    return Prompt(nome=nome, versao=versao, texto=caminho.read_text(encoding="utf-8").strip())


def delimitar(conteudo: str, origem: str) -> str:
    """Envolve conteúdo externo na etiqueta que o prompt de sistema manda tratar como dado.

    Uma etiqueta igual dentro do conteúdo é neutralizada; senão o documento
    poderia fechar o bloco e escrever instruções fora dele.
    """
    seguro = _ETIQUETA_NO_CONTEUDO.sub(r"&lt;\1" + ETIQUETA, conteudo)
    origem = re.sub(r"[^\w./-]", "_", origem)
    return f'<{ETIQUETA} origem="{origem}">\n{seguro}\n</{ETIQUETA}>'
