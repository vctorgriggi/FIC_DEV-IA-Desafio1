"""Visão e OCR (RF08): rota de visão multimodal da OpenAI.

Uma chamada devolve o texto bruto, a versão corrigida e os trechos incertos.
O arquivo original não é alterado; a comparação com o gabarito e a confirmação
humana dos dados críticos acontecem no fluxo.
"""

from __future__ import annotations

from .config import Config
from .entradas import ArquivoEntrada
from .llm_client import ClienteLLM, RespostaVazia, entrada_com_anexo, formato_json, ler_json
from .prompts import carregar_prompt
from .tipos import TextoExtraido

PROMPT_OCR = ("ocr", 1)
PROMPT_SISTEMA = ("sistema_seguro", 1)
LEGIBILIDADE = ("boa", "regular", "ruim")

ESQUEMA_OCR = {
    "type": "object",
    "properties": {
        "texto_bruto": {"type": "string"},
        "texto_revisado": {"type": "string"},
        "trechos_incertos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"trecho": {"type": "string"}, "motivo": {"type": "string"}},
                "required": ["trecho", "motivo"],
            },
        },
        "legibilidade": {"type": "string", "enum": list(LEGIBILIDADE)},
        "observacoes": {"type": "string"},
    },
    "required": ["texto_bruto", "texto_revisado", "trechos_incertos", "legibilidade", "observacoes"],
}


def extrair_texto(arquivo: ArquivoEntrada, *, cliente: ClienteLLM, config: Config) -> TextoExtraido:
    sistema = carregar_prompt(config, *PROMPT_SISTEMA)
    tarefa = carregar_prompt(config, *PROMPT_OCR)
    entrada = entrada_com_anexo(
        tarefa.texto, nome_arquivo=arquivo.caminho.name, mime_type=arquivo.mime_type, conteudo=arquivo.ler_bytes()
    )
    resposta = cliente.gerar(
        modelo=config.modelo("visao"),
        entrada=entrada,
        instrucao_sistema=sistema.texto,
        formato_resposta=formato_json(ESQUEMA_OCR, "ocr"),
    )
    dados = ler_json(resposta)

    bruto = str(dados.get("texto_bruto") or "").strip()
    if not bruto:
        raise RespostaVazia("O modelo não extraiu texto do documento.")
    revisado = str(dados.get("texto_revisado") or "").strip() or bruto
    incertos = [
        f"{str(item.get('trecho', '')).strip()} — {str(item.get('motivo', '')).strip()}"
        for item in dados.get("trechos_incertos") or []
        if isinstance(item, dict) and str(item.get("trecho", "")).strip()
    ]
    legibilidade = dados.get("legibilidade")
    return TextoExtraido(
        texto_bruto=bruto,
        texto_revisado=revisado,
        trechos_incertos=incertos,
        metadados={
            "rota": "visão multimodal na nuvem (OpenAI API)",
            "modelo": resposta.modelo,
            "mime_type": arquivo.mime_type,
            "sha256_original": arquivo.sha256,
            "legibilidade": legibilidade if legibilidade in LEGIBILIDADE else "não informada",
            "observacoes": str(dados.get("observacoes") or ""),
            "prompt_sistema": sistema.identificador,
        },
        resposta=resposta,
        prompt=tarefa,
    )
