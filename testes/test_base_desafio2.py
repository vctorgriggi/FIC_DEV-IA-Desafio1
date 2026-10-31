"""Base do Desafio 2: contratos, adaptador do provedor, manifesto do acervo, interface e comando.

As pendências de cada parte ficam em test_d2_nlp.py, test_d2_indice_rag.py e
test_d2_guardrails_sentimentos.py, um arquivo por estudante.
"""

import json
from types import SimpleNamespace

import httpx2
import openai
import pytest
from pydantic import BaseModel, ValidationError

from src import ingestion, metrics, revisao
from src.embeddings import IndiceVetorial
from src.entradas import ArquivoInvalido
from src.llm_client import ClienteLLM, LimiteRequisicoes, RespostaMalformada, ServicoIndisponivel, formato_json
from src.schemas import (
    AvaliacaoSentimento,
    DecisaoGuardrail,
    FichaCompreensao,
    RegistroMinutaRAG,
    RespostaGerada,
    SolicitacaoEstruturada,
    Trecho,
)
from testes import exemplos, falsos

# Modelos que o modelo de linguagem preenche: o esquema deles vai para o modo estrito.
SAIDAS_DO_MODELO = [SolicitacaoEstruturada, FichaCompreensao, RespostaGerada, AvaliacaoSentimento, DecisaoGuardrail]


# --- contratos (RF14, RF15, RF19) -------------------------------------------------


def test_solicitacao_aceita_null_e_lista_de_ausentes():
    solicitacao = exemplos.solicitacao(data=None, pedido=None, campos_ausentes=["data", "pedido"])
    assert solicitacao.data is None and solicitacao.campos_ausentes == ["data", "pedido"]


@pytest.mark.parametrize(
    ("alteracao", "tipo_erro"),
    [
        ({"extra": "x"}, "extra_forbidden"),
        ({"necessita_revisao": "true"}, "bool_type"),
        ({"necessita_revisao": 1}, "bool_type"),
        ({"protocolo": 2026}, "string_type"),
    ],
)
def test_esquema_distingue_chave_extra_e_tipo_incorreto_sem_coercao(alteracao, tipo_erro):
    dados = {**exemplos.solicitacao().model_dump(), **alteracao}
    with pytest.raises(ValidationError) as erro:
        SolicitacaoEstruturada(**dados)
    assert erro.value.errors()[0]["type"] == tipo_erro


def test_esquema_distingue_campo_obrigatorio_ausente():
    dados = exemplos.solicitacao().model_dump()
    del dados["categoria"]
    with pytest.raises(ValidationError) as erro:
        SolicitacaoEstruturada(**dados)
    assert erro.value.errors()[0]["type"] == "missing"


def test_resumo_acima_de_100_palavras_e_recusado():
    exemplos.ficha(resumo=" ".join(["palavra"] * 100))
    with pytest.raises(ValidationError, match="100 palavras"):
        exemplos.ficha(resumo=" ".join(["palavra"] * 101))


def objetos(esquema):
    if isinstance(esquema, dict):
        if esquema.get("type") == "object":
            yield esquema
        for valor in esquema.values():
            yield from objetos(valor)
    elif isinstance(esquema, list):
        for item in esquema:
            yield from objetos(item)


@pytest.mark.parametrize("modelo", SAIDAS_DO_MODELO, ids=lambda m: m.__name__)
def test_esquema_de_saida_e_compativel_com_o_modo_estrito(modelo: type[BaseModel]):
    esquema = formato_json(modelo.model_json_schema(), modelo.__name__)["format"]["schema"]
    for objeto in objetos(esquema):
        assert objeto["additionalProperties"] is False
        assert sorted(objeto["required"]) == sorted(objeto.get("properties", {}))
    assert '"default"' not in json.dumps(esquema)


def test_trecho_sem_pagina_e_secao_como_o_chroma_devolve():
    metadados_do_chroma = {k: v for k, v in exemplos.trecho().model_dump().items() if v is not None}
    assert Trecho(**metadados_do_chroma).pagina is None


def test_registro_da_minuta_relido_igual_e_fontes_por_afirmacao(config):
    registro = exemplos.registro("pendente")
    revisao.gravar_registro_rag(config, registro)
    assert revisao.ler_registro_rag(config, registro.id_execucao) == registro
    assert registro.resposta.fontes() == ["DOC-01:abc123:A:0"]
    bloqueada = exemplos.registro("bloqueada")
    assert bloqueada.resposta is None and bloqueada.guardrails[0].decisao == "bloquear"
    with pytest.raises(revisao.RevisaoInvalida):
        revisao.ler_registro_rag(config, "inexistente")


# --- adaptador do provedor (RF16, RF17, RF21) -------------------------------------------


def test_perfil_de_geracao_ativo_alternativo_e_provedor(config):
    assert config.perfil_geracao()["nome"] == config.dados["geracao"]["perfil_ativo"]
    assert config.perfil_geracao("alternativo")["modelo"] != config.perfil_geracao("principal")["modelo"]
    with pytest.raises(KeyError, match="não existe"):
        config.perfil_geracao("inexistente")
    config.dados["geracao"]["perfis"]["outro"] = {"provedor": "outro", "modelo": "x"}
    with pytest.raises(KeyError, match="sem adaptador"):
        config.perfil_geracao("outro")


def test_embeddings_na_ordem_da_entrada_com_dimensao_e_custo(config):
    sdk = falsos.SDKFalso(falsos.embeddings([[1.0, 0.0], [0.0, 1.0]], tokens=1000, embaralhar=True))
    obtido = ClienteLLM(config, chave="c", sdk=sdk).gerar_embeddings(modelo="text-embedding-3-small", textos=["a", "b"])
    assert obtido.vetores == [[1.0, 0.0], [0.0, 1.0]] and obtido.dimensao == 2
    assert obtido.custo_estimado_usd == pytest.approx(1000 * 0.02 / 1_000_000)
    with pytest.raises(RespostaMalformada):
        ClienteLLM(config, chave="c", sdk=falsos.SDKFalso(falsos.embeddings([[1.0]]))).gerar_embeddings(
            modelo="text-embedding-3-small", textos=["a", "b"])
    with pytest.raises(ValueError):
        ClienteLLM(config, chave="c", sdk=sdk).gerar_embeddings(modelo="text-embedding-3-small", textos=[])


def erro_http(classe, status):
    requisicao = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    return classe(f"Error code: {status}", response=httpx2.Response(status, request=requisicao), body=None)


class SDKQueFalhaUmaVez(falsos.SDKFalso):
    def __init__(self, erro):
        super().__init__()
        self._primeiro_erro = erro
        self.responses = SimpleNamespace(create=self._criar)

    def _criar(self, **argumentos):
        self.chamadas.append(argumentos)
        if len(self.chamadas) == 1:
            raise self._primeiro_erro
        return falsos.resposta("ok")


def test_falha_transitoria_repete_uma_vez_e_429_nao_repete(config):
    sdk = SDKQueFalhaUmaVez(erro_http(openai.InternalServerError, 503))
    assert ClienteLLM(config, chave="c", sdk=sdk).gerar(modelo="gpt-6.1-terra", entrada="oi").texto == "ok"
    assert len(sdk.chamadas) == 2
    sempre = falsos.SDKFalso(erro=erro_http(openai.InternalServerError, 503))
    with pytest.raises(ServicoIndisponivel):
        ClienteLLM(config, chave="c", sdk=sempre).gerar(modelo="gpt-6.1-terra", entrada="oi")
    assert len(sempre.chamadas) == 1 + config.dados["limites"]["repeticoes_falha_transitoria"]
    cota = SDKQueFalhaUmaVez(erro_http(openai.RateLimitError, 429))
    with pytest.raises(LimiteRequisicoes):
        ClienteLLM(config, chave="c", sdk=cota).gerar(modelo="gpt-6.1-terra", entrada="oi")
    assert len(cota.chamadas) == 1


def test_controle_de_recursos_e_avisado_em_cada_chamada(config):
    eventos = []
    controle = SimpleNamespace(antes_da_chamada=lambda: eventos.append("antes"), registrar=lambda t: eventos.append(t))
    cliente = ClienteLLM(config, chave="c", sdk=falsos.SDKFalso(falsos.resposta("ok", entrada=10, saida=5)), controle=controle)
    cliente.gerar(modelo="gpt-6.1-terra", entrada="oi")
    assert eventos == ["antes", 15]


# --- acervo e métricas ----------------------------------------------------------------


def gravar_manifesto(config, documentos, arquivos=()):
    pasta = config.caminho("acervo")
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "acervo.json").write_text(json.dumps({"versao_manifesto": 1, "documentos": documentos}), encoding="utf-8")
    for nome in arquivos:
        (pasta / nome).write_text("texto", encoding="utf-8")


def doc(id_, arquivo="a.txt", **extra):
    return {"id": id_, "titulo": "t", "versao": "1", "arquivo": arquivo, "tema": "x", **extra}


def test_manifesto_valido_com_vigencia_e_substituicao(config):
    gravar_manifesto(config, [doc("D1"), doc("D2", "b.txt", vigencia_inicio="2026-02-01", substitui=["D1"])], ["a.txt", "b.txt"])
    documentos = ingestion.ler_manifesto(config)
    assert str(documentos[1].vigencia_inicio) == "2026-02-01" and documentos[1].substitui == ["D1"]


@pytest.mark.parametrize(
    ("documentos", "arquivos", "mensagem"),
    [
        ([doc("D", "falta.txt")], [], "inexistente"),
        ([doc("D", "a.docx")], ["a.docx"], "extensão"),
        ([doc("D"), doc("D")], ["a.txt"], "repetido"),
        ([{"id": "D", "titulo": "t", "arquivo": "a.txt", "tema": "x"}], ["a.txt"], "inválido"),
        ([doc("D", substitui=["X"])], ["a.txt"], "substitui"),
        ([doc("D", substitui=["D"])], ["a.txt"], "substitui"),
    ],
)
def test_manifesto_invalido(config, documentos, arquivos, mensagem):
    gravar_manifesto(config, documentos, arquivos)
    with pytest.raises(ArquivoInvalido, match=mensagem):
        ingestion.ler_manifesto(config)


def test_manifesto_ausente(config):
    with pytest.raises(ArquivoInvalido, match="não encontrado"):
        ingestion.ler_manifesto(config)


def test_indice_valida_o_nome_do_chunking(config):
    assert IndiceVetorial(config, None).chunking == config.dados["indice"]["chunking_ativo"]
    with pytest.raises(KeyError, match="Chunking"):
        IndiceVetorial(config, None, chunking="principal")


def test_proporcao_mostra_os_dois_termos_e_nao_divide_por_zero():
    assert metrics.proporcao(3, 5) == {"numerador": 3, "denominador": 5, "valor": 0.6}
    assert metrics.proporcao(0, 0)["valor"] is None
    with pytest.raises(ValueError):
        metrics.proporcao(6, 5)


@pytest.mark.parametrize(
    ("conteudo", "mensagem"),
    [("{", "JSON"), ('[{"id": "A"}]', "lista"), ('[{"id": "A", "texto": "x"}, {"id": "A", "texto": "y"}]', "repetido")],
)
def test_avaliacoes_malformadas_viram_erro_claro(config, conteudo, mensagem):
    from src import sentiment

    pasta = config.caminho("avaliacoes")
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / sentiment.ARQUIVO_AVALIACOES).write_text(conteudo, encoding="utf-8")
    with pytest.raises(ArquivoInvalido, match=mensagem):
        sentiment.ler_avaliacoes(config)


# --- interface (RF20) e comando --------------------------------------------------------------


@pytest.fixture
def app_com_dados(config, monkeypatch):
    """Assistente com chave falsa, um documento no manifesto e uma avaliação: os botões ficam habilitados."""
    from streamlit.testing.v1 import AppTest

    from src.config import RAIZ

    gravar_manifesto(config, [doc("DOC-01")], ["a.txt"])
    pasta = config.caminho("avaliacoes")
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "avaliacoes.json").write_text('[{"id": "AV-01", "texto": "Gostei."}]', encoding="utf-8")
    monkeypatch.setattr("src.config.carregar_config", lambda: config)
    monkeypatch.setattr("src.llm_client.carregar_chave", lambda: "sk-teste-sem-rede")
    return AppTest.from_file(str(RAIZ / "src" / "app.py"), default_timeout=30)


def clicar(app, rotulo):
    next(b for b in app.button if b.label == rotulo).click().run()


@pytest.mark.parametrize(
    ("tela", "acao", "requisito"),
    [
        ("Acervo e índice", lambda app: clicar(app, "Indexar o acervo"), "RF17"),
        ("Acervo e índice", lambda app: clicar(app, "Excluir documento"), "RF24"),
        ("Solicitação", lambda app: (app.text_area[0].input("Pedido fictício.").run(), clicar(app, "Analisar e gerar minuta")), "RF"),
        ("Consulta ao acervo", lambda app: (app.text_input[0].input("Quais documentos?").run(), clicar(app, "Buscar trechos")), "RF17"),
        ("Consulta ao acervo", lambda app: (app.text_input[0].input("Quais documentos?").run(), clicar(app, "Responder com fontes")), "RF19"),
        ("Avaliações", lambda app: clicar(app, "Classificar avaliações"), "RF22"),
    ],
)
def test_botoes_do_assistente_chamam_as_partes_sem_excecao(app_com_dados, tela, acao, requisito):
    app = app_com_dados.run()
    app.sidebar.radio[0].set_value(tela).run()
    acao(app)
    assert not app.exception
    assert any(requisito in aviso.value for aviso in app.warning), [a.value for a in app.warning]


def test_registro_bloqueado_nao_mostra_decisao(app_com_dados):
    app = app_com_dados.run()
    app.sidebar.radio[0].set_value("Solicitação").run()
    app.session_state["registro"] = exemplos.registro("bloqueada")
    app.run()
    assert not app.exception and any("bloqueada" in e.value for e in app.error)
    assert not any(b.label == "Registrar decisão" for b in app.button)
    app.session_state["registro"] = exemplos.registro("pendente")
    app.run()
    assert any(b.label == "Registrar decisão" for b in app.button)


def test_comando_assistente_abre_o_streamlit_so_no_localhost(config, monkeypatch):
    from src import main as cli

    chamadas = []
    monkeypatch.setattr(cli, "carregar_config", lambda: config)
    monkeypatch.setattr(cli.subprocess, "run", lambda comando, **kw: chamadas.append((comando, kw)) or SimpleNamespace(returncode=0))
    assert cli.main(["assistente", "--porta", "8600"]) == 0
    comando, opcoes = chamadas[0]
    assert comando[1:4] == ["-m", "streamlit", "run"] and comando[4].endswith("src/app.py")
    assert comando[comando.index("--server.address") + 1] == "127.0.0.1"
    # Sem headless, a primeira execução para e pede um e-mail no terminal.
    assert comando[comando.index("--server.headless") + 1] == "true"
    assert opcoes["cwd"] == config.raiz
    monkeypatch.setattr(cli.subprocess, "run", lambda comando, **kw: SimpleNamespace(returncode=1))
    assert cli.main(["assistente"]) == 1
