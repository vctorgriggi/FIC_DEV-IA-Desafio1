"""Pendências do Estudante 3 — guardrails, Streamlit, sentimentos e painel (RF16, RF20, RF22). Ao implementar uma função, apague a linha dela e escreva os testes reais."""

import pytest

from src.llm_client import ClienteLLM
from src.tipos import PendenteDeImplementacao
from testes import exemplos, falsos
from src import guardrails, metrics, revisao, sentiment


def pendencias(config):
    cliente = ClienteLLM(config, chave="c", sdk=falsos.SDKFalso())
    return {
        "RF16 verificar_entrada": lambda: guardrails.verificar_entrada("x", config=config),
        "RF16 verificar_arquivo": lambda: guardrails.verificar_arquivo("a.txt", 10, config=config),
        "RF16 verificar_trechos": lambda: guardrails.verificar_trechos([], config=config),
        "RF16 verificar_saida": lambda: guardrails.verificar_saida(exemplos.resposta_rag(), config=config),
        "RF16 antes_da_chamada": lambda: guardrails.ControleRecursos(config).antes_da_chamada(),
        "RF16 registrar": lambda: guardrails.ControleRecursos(config).registrar(10),
        "RF20 registrar_decisao_rag": lambda: revisao.registrar_decisao_rag(config, None, "id", decisao="aprovar", justificativa="j", revisor="r"),
        "RF22 classificar": lambda: sentiment.classificar("AV-01", "x", cliente=cliente, config=config),
        "RF22 classificar_lote": lambda: sentiment.classificar_lote([], cliente=cliente, config=config),
        "RF22 agregar_sentimentos": lambda: metrics.agregar_sentimentos([exemplos.avaliacao()]),
    }


def test_partes_pendentes_avisam_qual_requisito_falta(config):
    for nome, chamada in pendencias(config).items():
        with pytest.raises(PendenteDeImplementacao) as erro:
            chamada()
        assert erro.value.requisito == nome.split()[0], nome
