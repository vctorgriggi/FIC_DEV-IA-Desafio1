"""Base do Desafio 2: contratos, perfis de geração, embeddings, manifesto do acervo e esqueletos."""

import json

import pytest
from pydantic import ValidationError

from src import embeddings, fluxo_rag, guardrails, ingestion, metrics, nlp, rag, revisao, sentiment
from src.entradas import ArquivoInvalido
from src.llm_client import ClienteLLM, RespostaMalformada
from src.schemas import DocumentoAcervo, Entidades, FichaCompreensao, SolicitacaoEstruturada
from src.tipos import PendenteDeImplementacao
from testes import falsos

SOLICITACAO = {
    "protocolo": "2026-000001", "data": None, "solicitante": "Pessoa Fictícia", "assunto": "Matrícula",
    "pedido": None, "categoria": "matricula", "entidades": {"pessoas": ["Pessoa Fictícia"]},
    "campos_ausentes": ["data", "pedido"], "necessita_revisao": True, "motivo_revisao": "campos ausentes",
}


# --- contratos (RF14, RF15) ---------------------------------------------------


def test_solicitacao_aceita_null_e_lista_de_ausentes():
    solicitacao = SolicitacaoEstruturada(**SOLICITACAO)
    assert solicitacao.data is None and solicitacao.campos_ausentes == ["data", "pedido"]
    assert solicitacao.entidades.orgaos == []


@pytest.mark.parametrize(
    ("alteracao", "tipo_erro"),
    [
        ({"extra": "x"}, "extra_forbidden"),
        ({"necessita_revisao": "talvez"}, "bool_parsing"),
        ({"protocolo": 2026}, "string_type"),
    ],
)
def test_esquema_distingue_chave_extra_tipo_incorreto(alteracao, tipo_erro):
    with pytest.raises(ValidationError) as erro:
        SolicitacaoEstruturada(**{**SOLICITACAO, **alteracao})
    assert erro.value.errors()[0]["type"] == tipo_erro


def test_esquema_distingue_campo_obrigatorio_ausente():
    incompleta = {k: v for k, v in SOLICITACAO.items() if k != "categoria"}
    with pytest.raises(ValidationError) as erro:
        SolicitacaoEstruturada(**incompleta)
    assert erro.value.errors()[0]["type"] == "missing"


def test_resumo_acima_de_100_palavras_e_recusado():
    ficha = {"categoria": "matricula", "entidades": Entidades(), "inferencias": []}
    FichaCompreensao(resumo=" ".join(["palavra"] * 100), **ficha)
    with pytest.raises(ValidationError, match="100 palavras"):
        FichaCompreensao(resumo=" ".join(["palavra"] * 101), **ficha)


# --- perfis de geração (RF21) e embeddings (RF17) -------------------------------------


def test_perfil_de_geracao_ativo_e_alternativo(config):
    assert config.perfil_geracao()["nome"] == config.dados["geracao"]["perfil_ativo"]
    assert config.perfil_geracao("alternativo")["modelo"] != config.perfil_geracao("principal")["modelo"]
    with pytest.raises(KeyError, match="não existe"):
        config.perfil_geracao("inexistente")


def test_embeddings_na_ordem_da_entrada_com_dimensao_e_custo(config):
    sdk = falsos.SDKFalso(falsos.embeddings([[1.0, 0.0], [0.0, 1.0]], tokens=1000, embaralhar=True))
    obtido = ClienteLLM(config, chave="c", sdk=sdk).gerar_embeddings(modelo="text-embedding-3-small", textos=["a", "b"])
    assert obtido.vetores == [[1.0, 0.0], [0.0, 1.0]]
    assert obtido.dimensao == 2
    assert obtido.custo_estimado_usd == pytest.approx(1000 * 0.02 / 1_000_000)
    assert sdk.chamadas[0]["_operacao"] == "embeddings.create" and sdk.chamadas[0]["input"] == ["a", "b"]


def test_embeddings_com_contagem_errada_ou_sem_texto(config):
    cliente = ClienteLLM(config, chave="c", sdk=falsos.SDKFalso(falsos.embeddings([[1.0]])))
    with pytest.raises(RespostaMalformada):
        cliente.gerar_embeddings(modelo="text-embedding-3-small", textos=["a", "b"])
    with pytest.raises(ValueError):
        cliente.gerar_embeddings(modelo="text-embedding-3-small", textos=[])


# --- manifesto do acervo -------------------------------------------------------------


def gravar_manifesto(config, documentos):
    pasta = config.caminho("acervo")
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "acervo.json").write_text(json.dumps({"versao_manifesto": 1, "documentos": documentos}), encoding="utf-8")
    return pasta


def test_manifesto_valido(config):
    pasta = gravar_manifesto(config, [{"id": "DOC-01", "titulo": "Guia", "versao": "1.0", "arquivo": "guia.txt",
                                        "tema": "matricula", "vigencia_inicio": "2026-02-01"}])
    (pasta / "guia.txt").write_text("texto", encoding="utf-8")
    documentos = ingestion.ler_manifesto(config)
    assert documentos[0].id == "DOC-01" and str(documentos[0].vigencia_inicio) == "2026-02-01"


@pytest.mark.parametrize(
    ("documentos", "arquivos", "mensagem"),
    [
        ([{"id": "D", "titulo": "t", "versao": "1", "arquivo": "falta.txt", "tema": "x"}], [], "inexistente"),
        ([{"id": "D", "titulo": "t", "versao": "1", "arquivo": "a.docx", "tema": "x"}], ["a.docx"], "extensão"),
        ([{"id": "D", "titulo": "t", "versao": "1", "arquivo": "a.txt", "tema": "x"}] * 2, ["a.txt"], "repetido"),
        ([{"id": "D", "titulo": "t", "arquivo": "a.txt", "tema": "x"}], ["a.txt"], "inválido"),
    ],
)
def test_manifesto_invalido(config, documentos, arquivos, mensagem):
    pasta = gravar_manifesto(config, documentos)
    for nome in arquivos:
        (pasta / nome).write_text("texto", encoding="utf-8")
    with pytest.raises(ArquivoInvalido, match=mensagem):
        ingestion.ler_manifesto(config)


def test_manifesto_ausente(config):
    with pytest.raises(ArquivoInvalido, match="não encontrado"):
        ingestion.ler_manifesto(config)


def test_manifesto_do_repositorio_e_valido():
    from src.config import carregar_config

    ingestion.ler_manifesto(carregar_config())


# --- métricas (RF23, T13) ----------------------------------------------------------


def test_proporcao_mostra_os_dois_termos_e_nao_divide_por_zero():
    assert metrics.proporcao(3, 5) == {"numerador": 3, "denominador": 5, "valor": 0.6}
    assert metrics.proporcao(0, 0)["valor"] is None
    with pytest.raises(ValueError):
        metrics.proporcao(6, 5)


# --- esqueletos pendentes ---------------------------------------------------------------


def chamadas_pendentes(config):
    cliente = ClienteLLM(config, chave="c", sdk=falsos.SDKFalso())
    indice = embeddings.IndiceVetorial(config, cliente)
    documento = DocumentoAcervo(id="D", titulo="t", versao="1", arquivo="a.txt", tema="x")
    solicitacao = SolicitacaoEstruturada(**SOLICITACAO)
    return {
        "RF17 extrair_texto": lambda: ingestion.extrair_texto(documento, config=config),
        "RF18 dividir": lambda: ingestion.dividir(documento, [], perfil="A", config=config),
        "RF17 indexar": lambda: indice.indexar(documento),
        "RF17 buscar": lambda: indice.buscar("x"),
        "RF24 excluir": lambda: indice.excluir("D"),
        "RF14 extrair_solicitacao": lambda: nlp.extrair_solicitacao("x", origem="o", cliente=cliente, config=config),
        "RF14 validar_regras": lambda: nlp.validar_regras(solicitacao, "x", config=config),
        "RF15 compreender": lambda: nlp.compreender("x", origem="o", cliente=cliente, config=config),
        "RF16 verificar_entrada": lambda: guardrails.verificar_entrada("x", config=config),
        "RF19 responder": lambda: rag.responder("x", indice=indice, cliente=cliente, config=config),
        "RF19 minuta": lambda: rag.minuta_fundamentada(solicitacao, "x", indice=indice, cliente=cliente, config=config),
        "RF19 fluxo": lambda: fluxo_rag.processar_solicitacao("x", origem="o", config=config, cliente=cliente,
                                                              indice=indice, auditoria=None),
        "RF20 decisao": lambda: revisao.registrar_decisao_rag(config, None, "id", decisao="aprovar",
                                                             justificativa="j", revisor="r"),
        "RF22 classificar": lambda: sentiment.classificar("A1", "x", cliente=cliente, config=config),
        "RF22 agregar": lambda: metrics.agregar_sentimentos([]),
    }


def test_partes_pendentes_avisam_qual_requisito_falta(config):
    for nome, chamada in chamadas_pendentes(config).items():
        with pytest.raises(PendenteDeImplementacao) as erro:
            chamada()
        assert erro.value.requisito == nome.split()[0], nome


# --- interface (RF20) ------------------------------------------------------------------


@pytest.mark.parametrize("tela", ["Acervo e índice", "Solicitação", "Consulta ao acervo", "Avaliações"])
def test_telas_do_assistente_abrem_sem_excecao(tela, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr("src.config.carregar_chave", lambda: None)
    monkeypatch.setattr("src.llm_client.carregar_chave", lambda: None)
    from src.config import RAIZ

    app = AppTest.from_file(str(RAIZ / "src" / "app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value(tela).run()
    assert not app.exception


def test_comando_assistente_abre_o_streamlit_so_no_localhost(config, monkeypatch):
    from src import main as cli

    chamadas = []
    monkeypatch.setattr(cli, "carregar_config", lambda: config)
    monkeypatch.setattr(cli.subprocess, "run", lambda comando, **kw: chamadas.append((comando, kw)))
    assert cli.main(["assistente", "--porta", "8600"]) == 0
    comando, opcoes = chamadas[0]
    assert comando[1:4] == ["-m", "streamlit", "run"] and comando[4].endswith("src/app.py")
    assert comando[comando.index("--server.address") + 1] == "127.0.0.1"
    # Sem headless, a primeira execução para e pede um e-mail no terminal.
    assert comando[comando.index("--server.headless") + 1] == "true"
    assert opcoes["cwd"] == config.raiz
