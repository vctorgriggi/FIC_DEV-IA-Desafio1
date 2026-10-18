"""Geração da minuta institucional (RF09).

O modelo redige o corpo; cabeçalho (brasão, órgão, dados de referência) e
fontes entram por código, para não dependerem do modelo lembrar deles nem
reescrever dados já confirmados.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .config import Config
from .extracao import CAMPOS_OBRIGATORIOS, NAO_LOCALIZADO
from .llm_client import ClienteLLM, RespostaLLM
from .prompts import Prompt, carregar_prompt, delimitar

PROMPT_MINUTA = ("minuta", 2)
PROMPT_SISTEMA = ("sistema_seguro", 1)
ORGAO = "GOVERNO DO ESTADO DE MATO GROSSO — CENTRAL DE ATENDIMENTO"
ROTULOS_REFERENCIA = (
    ("protocolo", "Protocolo"),
    ("data", "Data da solicitação"),
    ("solicitante", "Interessado(a)"),
    ("assunto", "Assunto"),
)
# motivo_revisao e confiança ficam de fora: servem à revisão, não à minuta, e
# motivo_revisao pode descrever a própria tentativa de injeção.
CAMPOS_PARA_MINUTA = (*CAMPOS_OBRIGATORIOS, "categoria", "campos_ausentes")


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


def contexto_minuta(campos: dict) -> str:
    """Campos da solicitação como conteúdo externo (RF03): vêm do texto do cidadão."""
    enviados = {campo: campos.get(campo, NAO_LOCALIZADO) for campo in CAMPOS_PARA_MINUTA}
    return delimitar(json.dumps(enviados, ensure_ascii=False, indent=2), "campos_extraidos")


def gerar_minuta(campos: dict, *, fontes: list[str], cliente: ClienteLLM, config: Config) -> Minuta:
    """Minuta para revisão humana; não existe envio (revisao.py é o ponto final)."""
    sistema = carregar_prompt(config, *PROMPT_SISTEMA)
    prompt = carregar_prompt(config, *PROMPT_MINUTA)
    resposta = cliente.gerar(
        modelo=config.modelo("texto"),
        entrada=f"{prompt.texto}\n\n{contexto_minuta(campos)}",
        instrucao_sistema=sistema.texto,
        saida="texto",
    )
    texto = "\n\n".join([cabecalho(campos, config), resposta.texto.strip(), secao_fontes(fontes)]) + "\n"
    return Minuta(
        texto=texto,
        campos_ausentes=[str(c) for c in campos.get("campos_ausentes", [])],
        fontes=fontes,
        resposta=resposta,
        prompt=prompt,
    )


def cabecalho(campos: dict, config: Config) -> str:
    # A minuta é gravada em resultados/minutas/; o caminho do brasão é relativo a essa pasta.
    brasao = os.path.relpath(config.raiz / config.dados["imagem_institucional"], config.caminho("minutas"))
    linhas = [f"![Brasão Oficial]({brasao.replace(os.sep, '/')})", "", f"**{ORGAO}**", "", "### Dados de referência"]
    linhas += [f"- **{rotulo}:** {campos.get(campo) or NAO_LOCALIZADO}" for campo, rotulo in ROTULOS_REFERENCIA]
    return "\n".join(linhas)


def secao_fontes(fontes: list[str]) -> str:
    return "\n".join(["### Fontes consultadas", *(f"- `{fonte}`" for fonte in fontes)])
