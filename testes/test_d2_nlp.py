"""Pendências do Estudante 1 — esquemas, NLP, dados e gabaritos (RF14, RF15). Ao implementar uma função, apague a linha dela e escreva os testes reais."""

import pytest

from src.llm_client import ClienteLLM
from src.tipos import PendenteDeImplementacao
from testes import exemplos, falsos
from src import metrics, nlp


def pendencias(config):
    cliente = ClienteLLM(config, chave="c", sdk=falsos.SDKFalso())
    return {
        "RF14 extrair_solicitacao": lambda: nlp.extrair_solicitacao("x", origem="o", cliente=cliente, config=config),
        "RF14 validar_regras": lambda: nlp.validar_regras(exemplos.solicitacao(), "x", config=config),
        "RF14 comparar_sintatico_e_esquema": lambda: nlp.comparar_sintatico_e_esquema("x", origem="o", cliente=cliente, config=config),
        "RF15 compreender": lambda: nlp.compreender("x", exemplos.solicitacao(), origem="o", cliente=cliente, config=config),
        "RF15 acuracia_categorias": lambda: metrics.acuracia_categorias({}, {}),
    }


def test_partes_pendentes_avisam_qual_requisito_falta(config):
    for nome, chamada in pendencias(config).items():
        with pytest.raises(PendenteDeImplementacao) as erro:
            chamada()
        assert erro.value.requisito == nome.split()[0], nome
