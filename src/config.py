"""Configuração (RF01): parâmetros não sensíveis em config.json, segredos no .env."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
VARIAVEL_CHAVE = "OPENAI_API_KEY"
BIBLIOTECAS_PRINCIPAIS = ("openai", "python-dotenv", "pillow", "fastapi", "uvicorn", "pytest")


class CasoInexistente(LookupError):
    pass


@dataclass(frozen=True)
class Config:
    dados: dict
    raiz: Path

    def caminho(self, nome: str) -> Path:
        return self.raiz / self.dados["caminhos"][nome]

    def modelo(self, tarefa: str) -> str:
        return self.dados["modelos"][tarefa]

    def perfil_geracao(self, nome: str | None = None) -> dict:
        """RF21: provedor e modelo de geração do perfil pedido, ou do ativo no config.

        Trocar de perfil não toca o índice: embeddings têm modelo próprio (modelos.embeddings).
        """
        geracao = self.dados["geracao"]
        nome = nome or geracao["perfil_ativo"]
        if nome not in geracao["perfis"]:
            raise KeyError(f"Perfil de geração '{nome}' não existe. Perfis: {', '.join(geracao['perfis'])}.")
        perfil = {"nome": nome, **geracao["perfis"][nome]}
        # Só há um adaptador (ClienteLLM, OpenAI); outro provedor pede outro adaptador, não só outro nome.
        if perfil["provedor"] != self.dados["provedor"]:
            raise KeyError(f"Perfil '{nome}' usa o provedor '{perfil['provedor']}', sem adaptador neste projeto.")
        return perfil

    def caso(self, caso_id: str) -> dict:
        for caso in self.dados["casos"]:
            if caso["id"] == caso_id:
                return caso
        ids = ", ".join(c["id"] for c in self.dados["casos"])
        raise CasoInexistente(f"Caso '{caso_id}' não existe no config.json. Casos: {ids}.")

    def relativo(self, caminho: Path) -> str:
        """Caminho relativo à raiz, para logs e referências portáveis entre máquinas."""
        try:
            return caminho.resolve().relative_to(self.raiz.resolve()).as_posix()
        except ValueError:
            return caminho.as_posix()


def carregar_config(caminho: Path | None = None) -> Config:
    caminho = caminho or RAIZ / "config.json"
    with open(caminho, encoding="utf-8") as arquivo:
        return Config(dados=json.load(arquivo), raiz=caminho.parent)


def carregar_chave() -> str | None:
    load_dotenv(RAIZ / ".env")
    return os.getenv(VARIAVEL_CHAVE, "").strip() or None


def versoes() -> dict[str, str]:
    encontradas = {"python": platform.python_version()}
    for biblioteca in BIBLIOTECAS_PRINCIPAIS:
        try:
            encontradas[biblioteca] = metadata.version(biblioteca)
        except metadata.PackageNotFoundError:
            encontradas[biblioteca] = "não instalada"
    return encontradas
