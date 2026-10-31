"""Pendências do Estudante 2 — embeddings, índice, RAG e provedor (RF17, RF18, RF19, RF21, RF24). Ao implementar uma função, apague a linha dela e escreva os testes reais."""

import pytest

from src.llm_client import ClienteLLM
from src.tipos import PendenteDeImplementacao
from testes import exemplos, falsos
from src import fluxo_rag, ingestion, metrics, rag
from src.embeddings import IndiceVetorial
from src.schemas import DocumentoAcervo


def pendencias(config):
    cliente = ClienteLLM(config, chave="c", sdk=falsos.SDKFalso())
    indice = IndiceVetorial(config, cliente)
    documento = DocumentoAcervo(id="D", titulo="t", versao="1", arquivo="a.txt", tema="x")
    return {
        "RF17 extrair_texto": lambda: ingestion.extrair_texto(documento, config=config),
        "RF18 dividir": lambda: ingestion.dividir(documento, [], perfil="A", config=config),
        "RF20 incluir_documento": lambda: ingestion.incluir_documento(config, nome_arquivo="a.txt", conteudo=b"x", metadados={}, auditoria=None),
        "RF24 excluir_documento": lambda: ingestion.excluir_documento(config, "D", indice=indice, auditoria=None),
        "RF17 indexar": lambda: indice.indexar(documento),
        "RF17 buscar": lambda: indice.buscar("x"),
        "RF24 excluir": lambda: indice.excluir("D"),
        "RF17 contar": lambda: indice.contar(),
        "RF17 info": lambda: indice.info(),
        "RF17 desatualizados": lambda: indice.desatualizados([documento]),
        "RF18 acerto_recuperacao": lambda: metrics.acerto_recuperacao({}, {}),
        "RF19 responder": lambda: rag.responder("x", indice=indice, cliente=cliente, config=config),
        "RF19 minuta_fundamentada": lambda: rag.minuta_fundamentada(exemplos.solicitacao(), "x", indice=indice, cliente=cliente, config=config),
        "RF19 processar_solicitacao": lambda: fluxo_rag.processar_solicitacao("x", origem="o", config=config, cliente=cliente, indice=indice, auditoria=None),
    }


def test_partes_pendentes_avisam_qual_requisito_falta(config):
    for nome, chamada in pendencias(config).items():
        with pytest.raises(PendenteDeImplementacao) as erro:
            chamada()
        assert erro.value.requisito == nome.split()[0], nome
