"""Compreensão (RF05): campos estruturados a partir do texto da solicitação.

As três modalidades terminam aqui: texto direto, transcrição do áudio ou texto
do OCR. O esquema e a normalização são o contrato entre as partes; mudar um
campo muda o que a minuta, a revisão e os gabaritos recebem.
"""

from __future__ import annotations

from dataclasses import dataclass

import json

from .config import Config
from .llm_client import ClienteLLM, RespostaLLM, formato_json
from .prompts import Prompt, carregar_prompt, delimitar
from .tipos import PendenteDeImplementacao

NAO_LOCALIZADO = "não localizado"
CAMPOS_OBRIGATORIOS = ("protocolo", "data", "solicitante", "assunto", "pedido")
NIVEIS_CONFIANCA = ("alta", "media", "baixa")


@dataclass
class ResultadoExtracao:
    campos: dict
    resposta: RespostaLLM | None = None
    prompt: Prompt | None = None


def esquema_extracao(categorias: list[str]) -> dict:
    """Esquema JSON pedido ao modelo; categorias vêm de config.json (lista documentada)."""
    categoria: dict = {"type": "string"}
    if categorias:
        categoria["enum"] = [*categorias, NAO_LOCALIZADO]
    literal = {"type": "string", "description": f"Valor presente na entrada ou '{NAO_LOCALIZADO}'."}
    return {
        "type": "object",
        "properties": {
            **{campo: literal for campo in CAMPOS_OBRIGATORIOS},
            "categoria": categoria,
            "campos_ausentes": {"type": "array", "items": {"type": "string"}},
            "confianca": {"type": "string", "enum": list(NIVEIS_CONFIANCA)},
            "necessita_revisao": {"type": "boolean"},
            "motivo_revisao": {"type": "string"},
        },
        "required": [*CAMPOS_OBRIGATORIOS, "categoria", "campos_ausentes", "confianca", "necessita_revisao", "motivo_revisao"],
    }


def normalizar_extracao(dados: object, categorias: list[str]) -> dict:
    """Devolve sempre o mesmo formato, mesmo com campos ausentes ou resposta malformada.

    Critério de aceite do RF05. campos_ausentes é recalculado aqui em vez de
    confiar só no modelo, e qualquer ausência força necessita_revisao.
    """
    dados = dados if isinstance(dados, dict) else {}
    campos: dict = {}
    for campo in CAMPOS_OBRIGATORIOS:
        valor = dados.get(campo)
        campos[campo] = valor.strip() if isinstance(valor, str) and valor.strip() else NAO_LOCALIZADO

    categoria = dados.get("categoria")
    valida = isinstance(categoria, str) and categoria.strip() and (not categorias or categoria in categorias)
    campos["categoria"] = categoria.strip() if valida else NAO_LOCALIZADO

    calculados = {c for c in (*CAMPOS_OBRIGATORIOS, "categoria") if campos[c] == NAO_LOCALIZADO}
    informados = {c for c in dados.get("campos_ausentes") or [] if isinstance(c, str)}
    campos["campos_ausentes"] = sorted(calculados | informados)

    confianca = dados.get("confianca")
    campos["confianca"] = confianca if confianca in NIVEIS_CONFIANCA else "baixa"
    campos["necessita_revisao"] = (
        dados.get("necessita_revisao") is not False or bool(campos["campos_ausentes"]) or campos["confianca"] == "baixa"
    )
    campos["motivo_revisao"] = str(dados.get("motivo_revisao") or "")
    return campos


def extrair_campos(texto: str, *, origem: str, cliente: ClienteLLM, config: Config) -> ResultadoExtracao:
    """RF05 — parte: texto.

    Esperado:
    - carregar o prompt de sistema seguro e o de extração (prompts.carregar_prompt);
    - mandar o texto dentro de prompts.delimitar(texto, origem), nunca solto no prompt;
    - pedir saída com llm_client.formato_json(esquema_extracao(config.dados["categorias"]));
    - passar o JSON devolvido por normalizar_extracao, também quando json.loads falhar.
    O texto chega já mascarado (privacidade.mascarar); o original fica com o fluxo.
    """
    prompt_sistema = carregar_prompt(config, "sistema_seguro", 1)
    prompt_extracao = carregar_prompt(config, "extracao", 1)

    conteudo_delimitado = delimitar(texto, origem)
    entrada = f"{prompt_extracao.texto}\n\n{conteudo_delimitado}"

    categorias = config.dados.get("categorias", [])
    esquema = esquema_extracao(categorias)
    formato = formato_json(esquema)

    resposta = cliente.gerar(
        modelo=config.modelo("texto"),
        entrada=entrada,
        instrucao_sistema=prompt_sistema.texto,
        formato_resposta=formato,
        saida="texto",
    )

    try:
        dados = json.loads(resposta.texto)
    except json.JSONDecodeError:
        # Critério do RF05: o JSON final continua válido; o motivo avisa o revisor.
        dados = {"motivo_revisao": "Resposta do modelo fora do formato JSON; nenhum campo foi extraído."}

    campos = normalizar_extracao(dados, categorias)
    return ResultadoExtracao(campos=campos, resposta=resposta, prompt=prompt_extracao)

