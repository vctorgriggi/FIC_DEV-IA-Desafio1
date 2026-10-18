"""Experimento de prompts do RF02: a mesma tarefa de redação com os prompts A, B e C.

Mesmo modelo, mesmos parâmetros, mesmo prompt de sistema e mesma entrada
(campos, fontes e imagem institucional, delimitados); muda só o prompt da
tarefa. Saídas e métricas ficam em resultados/experimentos/<id>/ e cada
chamada vira um evento na auditoria.
"""

from __future__ import annotations

import json

from .audit import Auditoria, Evento, agora_iso, novo_id
from .config import Config
from .llm_client import ClienteLLM
from .minuta import PROMPT_SISTEMA
from .prompts import carregar_prompt, delimitar

PROMPTS = {"A": ("minuta_a", 1), "B": ("minuta_b", 1), "C": ("minuta_c", 1)}


def executar_experimento(
    entrada: dict, *, origem: str, config: Config, cliente: ClienteLLM, auditoria: Auditoria
) -> dict:
    id_execucao = novo_id()
    pasta = config.caminho("experimentos") / id_execucao
    pasta.mkdir(parents=True)
    sistema = carregar_prompt(config, *PROMPT_SISTEMA)
    contexto = delimitar(json.dumps(entrada, ensure_ascii=False, indent=2), "campos_extraidos")
    modelo = config.modelo("texto")

    resultados = {}
    for rotulo, (nome, versao) in PROMPTS.items():
        prompt = carregar_prompt(config, nome, versao)
        resposta = cliente.gerar(modelo=modelo, entrada=f"{prompt.texto}\n\n{contexto}", instrucao_sistema=sistema.texto)
        saida = pasta / f"prompt_{rotulo}.md"
        saida.write_text(resposta.texto, encoding="utf-8")
        auditoria.registrar(
            Evento(
                id_execucao=id_execucao,
                caso_id="experimento-rf02",
                etapa=f"experimento_prompt_{rotulo}",
                modalidade="texto",
                arquivo_origem=origem,
                versao_prompt=prompt.identificador,
                hash_prompt=prompt.hash,
                saida=config.relativo(saida),
            ).com_resposta(resposta)
        )
        resultados[rotulo] = {
            "prompt": prompt.identificador,
            "saida": config.relativo(saida),
            "duracao_s": resposta.duracao_s,
            "tokens_entrada": resposta.tokens_entrada,
            "tokens_saida": resposta.tokens_saida,
            "custo_estimado_usd": resposta.custo_estimado_usd,
            "parametros": resposta.parametros,
        }

    metricas = {
        "id_execucao": id_execucao,
        "data_hora": agora_iso(),
        "modelo": modelo,
        "prompt_sistema": sistema.identificador,
        "entrada": origem,
        "resultados": resultados,
    }
    (pasta / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    return metricas
