"""Orçamento da missão real: testes não fazem rede nem leem a chave."""
import pytest

from scripts.orcamento_nlp import ClienteOrcamentado, OrcamentoEsgotado
from src.llm_client import ServicoIndisponivel
from testes import falsos


def test_bloqueia_antes_do_sdk_se_nao_ha_reserva_suficiente(config,tmp_path):
    sdk=falsos.SDKFalso()
    cliente=ClienteOrcamentado(config,arquivo=tmp_path/'ledger.json',limite=0.001,sdk=sdk,chave='teste')
    with pytest.raises(OrcamentoEsgotado):
        cliente.gerar(modelo=config.modelo('texto'),entrada='teste')
    assert not sdk.chamadas


def test_usage_e_custo_sao_persistidos_e_reutilizados(config,tmp_path):
    sdk=falsos.SDKFalso(falsos.resposta('ok',entrada=1000,saida=1000))
    arquivo=tmp_path/'ledger.json'
    cliente=ClienteOrcamentado(config,arquivo=arquivo,sdk=sdk,chave='teste')
    cliente.gerar(modelo=config.modelo('texto'),entrada='teste')
    assert cliente.gasto==pytest.approx(0.006)
    relido=ClienteOrcamentado(config,arquivo=arquivo,sdk=sdk,chave='teste')
    assert relido.gasto==cliente.gasto
    assert relido.ledger['chamadas'][0]['status']=='medido'
    assert 'teste' not in arquivo.read_text()


def test_repeticao_transitoria_reserva_cada_transporte(config,tmp_path):
    erro=type('FalhaTransitoria',(Exception,),{'status_code':503})('indisponível')
    sdk=falsos.SDKFalso(erro=erro)
    cliente=ClienteOrcamentado(config,arquivo=tmp_path/'ledger.json',sdk=sdk,chave='teste')
    with pytest.raises(ServicoIndisponivel):
        cliente.gerar(modelo=config.modelo('texto'),entrada='teste')
    assert len(sdk.chamadas)==len(cliente.ledger['chamadas'])==2
    assert all(c['custo_estimado_usd'] is None for c in cliente.ledger['chamadas'])
    assert cliente.gasto>0


def test_limite_tambem_interrompe_repeticao_transitoria(config,tmp_path):
    erro=type('FalhaTransitoria',(Exception,),{'status_code':503})('indisponível')
    sdk=falsos.SDKFalso(erro=erro)
    cliente=ClienteOrcamentado(config,arquivo=tmp_path/'ledger.json',limite=0.2,sdk=sdk,chave='teste')
    with pytest.raises(OrcamentoEsgotado):
        cliente.gerar(modelo=config.modelo('texto'),entrada='teste')
    assert len(sdk.chamadas)==1
    assert cliente.gasto<=0.2


def test_preco_desconhecido_bloqueia_chamada(config,tmp_path):
    sdk=falsos.SDKFalso()
    cliente=ClienteOrcamentado(config,arquivo=tmp_path/'ledger.json',sdk=sdk,chave='teste')
    with pytest.raises(OrcamentoEsgotado):
        cliente.gerar(modelo='modelo-sem-preco',entrada='teste')
    assert not sdk.chamadas
