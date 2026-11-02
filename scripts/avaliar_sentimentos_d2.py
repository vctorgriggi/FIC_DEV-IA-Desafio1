"""Avaliação real do RF22 contra o gabarito D2-sentimentos (chama a API: uma chamada por avaliação).

python -m scripts.avaliar_sentimentos_d2
python -m scripts.avaliar_sentimentos_d2 --perfil alternativo

Usa o mesmo caminho da tela "Avaliações" (sentiment.classificar_lote), que grava o lote em
resultados/metricas/sentimentos.json e um evento "sentimento" por avaliação na auditoria. Esta saída
acrescenta conferência contra o gabarito, painel, tokens e custo, em resultados/metricas/, fora do git.
"""

from __future__ import annotations

import argparse
import json
import sys

from src import metrics, sentiment
from src.audit import agora_iso
from src.config import carregar_config
from src.llm_client import ClienteLLM
from src.prompts import carregar_prompt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--perfil", default=None)
    args = parser.parse_args()
    config = carregar_config()
    perfil = config.perfil_geracao(args.perfil)
    prompt = carregar_prompt(config, "sentimento", 1)
    avaliacoes = sentiment.ler_avaliacoes(config)
    gabarito = sentiment.ler_gabarito(config)
    executado_em = agora_iso()
    resultados = sentiment.classificar_lote(avaliacoes, cliente=ClienteLLM(config), config=config, perfil=perfil["nome"])

    classificadas = [r.valor for r in resultados]
    conferencia = metrics.conferir_sentimentos(classificadas, gabarito)
    respostas = [r.respostas[-1] if r.respostas else None for r in resultados]
    por_avaliacao = [
        {
            **linha,
            "necessita_revisao": valor.necessita_revisao,
            "justificativa": valor.justificativa,
            "confianca_declarada": valor.confianca_declarada,
            "chamadas": len(resultado.respostas),
            "tokens_entrada": resposta.tokens_entrada if resposta else None,
            "tokens_saida": resposta.tokens_saida if resposta else None,
            "custo_estimado_usd": resposta.custo_estimado_usd if resposta else None,
        }
        for linha, valor, resultado, resposta in zip(conferencia["avaliacoes"], classificadas, resultados, respostas)
    ]
    saida = {
        "executado_em": executado_em,
        "perfil": perfil["nome"],
        "modelo": perfil["modelo"],
        "prompt": {"identificador": prompt.identificador, "hash": prompt.hash},
        "gabarito": "dados/gabaritos/D2-sentimentos.json",
        "acuracia": conferencia["acuracia"],
        "ambiguas_indeterminadas_com_revisao": metrics.proporcao(
            sum(1 for linha, valor in zip(por_avaliacao, classificadas)
                if linha["esperada"] == "indeterminada" and valor.polaridade == "indeterminada" and valor.necessita_revisao),
            sum(1 for linha in por_avaliacao if linha["esperada"] == "indeterminada"),
        ),
        "painel": metrics.agregar_sentimentos(classificadas),
        "tokens_entrada": sum(r.tokens_entrada or 0 for r in respostas if r),
        "tokens_saida": sum(r.tokens_saida or 0 for r in respostas if r),
        "custo_estimado_usd": round(sum(r.custo_estimado_usd or 0 for r in respostas if r), 6),
        "avaliacoes": por_avaliacao,
    }
    caminho = config.caminho("metricas") / f"sentimentos-d2-{perfil['nome']}.json"
    caminho.write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    taxa = saida["acuracia"]
    print(f"{taxa['numerador']}/{taxa['denominador']} iguais ao gabarito; saída em {config.relativo(caminho)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
