"""API da interface, com o SDK e as partes de IA substituídos; nenhuma chamada real."""

import base64
import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src import fluxo
from src.extracao import ResultadoExtracao
from src.llm_client import ChaveAusente
from src.minuta import Minuta
from src.revisao import CHECKLIST_PECA
from src.tipos import TextoExtraido
from src.web import criar_app
from testes.falsos import SDKFalso, interacao

CAMPOS = {"protocolo": "2024-000142", "data": "14/10/2026", "solicitante": "MARCUS", "assunto": "Matrícula",
          "pedido": "Matrícula", "categoria": "matricula", "campos_ausentes": []}


@pytest.fixture
def api(config, monkeypatch):
    monkeypatch.setattr(fluxo, "extrair_campos", lambda texto, **_: ResultadoExtracao(campos=dict(CAMPOS)))
    monkeypatch.setattr(fluxo, "gerar_minuta", lambda campos, *, fontes, **_: Minuta(
        texto=f"Protocolo {campos['protocolo']} — {campos['solicitante']}", campos_ausentes=[], fontes=fontes))
    monkeypatch.setattr(fluxo.vision, "extrair_texto", lambda arquivo, **_: TextoExtraido(
        texto_bruto="CÓDIGO: 2024-000142", texto_revisado="CÓDIGO: 2024-000142", trechos_incertos=["2024 — rasura"]))
    return TestClient(criar_app(config, fabrica_cliente=lambda: None))


def test_painel_vazio_lista_casos(api):
    painel = api.get("/api/painel").json()
    assert [c["id"] for c in painel["casos"]] == ["texto-01", "texto-injection", "audio-01", "imagem-01"]
    assert painel["minutas"] == [] and painel["pendentes"] == [] and painel["pecas"] == []
    assert set(painel["checklist_peca"]) == set(CHECKLIST_PECA)


def test_arquivo_so_serve_dados_e_resultados(api, config):
    (config.raiz / ".env").write_text("GEMINI_API_KEY=segredo", encoding="utf-8")
    assert api.get("/api/arquivo", params={"caminho": "dados/originais/entrada_texto.txt"}).status_code == 200
    for caminho in (".env", "../.env", "dados/../.env", "prompts/sistema_seguro_v1.md", "/etc/passwd"):
        resposta = api.get("/api/arquivo", params={"caminho": caminho})
        assert resposta.status_code == 404, caminho
        assert "segredo" not in resposta.text


def test_texto_vai_direto_para_minuta(api):
    resposta = api.post("/api/casos/texto-01/processar")
    assert resposta.status_code == 200 and "minuta" in resposta.json()
    minuta = api.get(f"/api/minutas/{resposta.json()['minuta']}").json()
    assert minuta["status"] == "aguardando_revisao" and minuta["texto"].startswith("Protocolo 2024-000142")


def test_imagem_espera_confirmacao_humana_e_aplica_correcao(api):
    id_execucao = api.post("/api/casos/imagem-01/processar").json()["confirmacao"]
    painel = api.get("/api/painel").json()
    assert [p["id_execucao"] for p in painel["pendentes"]] == [id_execucao]

    execucao = api.get(f"/api/execucoes/{id_execucao}").json()
    assert execucao["trechos_incertos"] == ["2024 — rasura"] and execucao["texto_bruto"].startswith("CÓDIGO")
    assert "comparacao" not in json.dumps(execucao)  # o gabarito não aparece para quem confirma

    sem_revisor = api.post(f"/api/execucoes/{id_execucao}/confirmar", json={"campos": {}, "revisor": " "})
    assert sem_revisor.status_code == 400

    campos = {"protocolo": "2026-000142", "data": "14/10/2026", "solicitante": "Marcos Vinícius de Almeida Santos"}
    resposta = api.post(f"/api/execucoes/{id_execucao}/confirmar", json={"campos": campos, "revisor": "Servidor A"})
    minuta = api.get(f"/api/minutas/{resposta.json()['minuta']}").json()
    assert minuta["texto"] == "Protocolo 2026-000142 — Marcos Vinícius de Almeida Santos"
    assert minuta["campos_corrigidos_por_humano"] == ["protocolo", "solicitante"]
    assert api.get("/api/painel").json()["pendentes"] == []


def test_decisao_com_correcao_grava_texto_e_trava_depois(api, config):
    id_minuta = api.post("/api/casos/texto-01/processar").json()["minuta"]
    sem_texto = {"decisao": "aprovar_com_correcao", "justificativa": "Ajuste", "revisor": "Servidor A"}
    assert api.post(f"/api/minutas/{id_minuta}/decisao", json=sem_texto).status_code == 400

    corrigida = {**sem_texto, "texto_corrigido": "Texto corrigido pelo servidor."}
    resposta = api.post(f"/api/minutas/{id_minuta}/decisao", json=corrigida)
    assert resposta.status_code == 200 and resposta.json()["status"] == "aprovada_com_correcao"
    arquivo = config.raiz / resposta.json()["arquivo_minuta"]
    assert arquivo.read_text(encoding="utf-8") == "Texto corrigido pelo servidor.\n"

    outra = api.post(f"/api/minutas/{id_minuta}/decisao", json={**corrigida, "texto_corrigido": "Mudança tardia"})
    assert outra.status_code == 400
    assert arquivo.read_text(encoding="utf-8") == "Texto corrigido pelo servidor.\n"


def test_decisao_invalida_nao_altera_a_minuta(api, config):
    id_minuta = api.post("/api/casos/texto-01/processar").json()["minuta"]
    arquivo = config.raiz / api.get(f"/api/minutas/{id_minuta}").json()["arquivo_minuta"]
    original = arquivo.read_text(encoding="utf-8")
    sem_justificativa = {"decisao": "aprovar_com_correcao", "justificativa": "", "revisor": "A", "texto_corrigido": "x"}
    assert api.post(f"/api/minutas/{id_minuta}/decisao", json=sem_justificativa).status_code == 400
    texto_sem_correcao = {"decisao": "rejeitar", "justificativa": "j", "revisor": "A", "texto_corrigido": "x"}
    assert api.post(f"/api/minutas/{id_minuta}/decisao", json=texto_sem_correcao).status_code == 400
    assert arquivo.read_text(encoding="utf-8") == original


def test_erro_de_provedor_e_caso_inexistente_viram_mensagens(config):
    def sem_chave():
        raise ChaveAusente()

    api = TestClient(criar_app(config, fabrica_cliente=sem_chave))
    resposta = api.post("/api/casos/texto-01/processar")
    assert resposta.status_code == 502 and "GEMINI_API_KEY" in resposta.json()["erro"]
    assert api.post("/api/casos/nao-existe/processar").status_code == 400


def test_peca_gerada_e_revisada_pela_api(config):
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "#88aacc").save(buffer, format="PNG")
    resposta_sdk = interacao("", imagem=base64.b64encode(buffer.getvalue()).decode("ascii"))
    from src.llm_client import ClienteLLM

    api = TestClient(criar_app(config, fabrica_cliente=lambda: ClienteLLM(config, chave="c", sdk=SDKFalso(resposta_sdk))))
    id_peca = api.post("/api/pecas", json={"caso_id": "imagem-01"}).json()["peca"]
    peca = api.get(f"/api/pecas/{id_peca}").json()
    assert peca["status"] == "aguardando_revisao"
    assert api.get("/api/arquivo", params={"caminho": peca["imagem"]}).headers["content-type"] == "image/png"

    tudo_ok = {chave: True for chave in CHECKLIST_PECA}
    corpo = {"checklist": tudo_ok, "decisao": "aprovar", "justificativa": "Conferida", "revisor": "Servidor A"}
    assert api.post(f"/api/pecas/{id_peca}/decisao", json=corpo).json()["status"] == "aprovada"
    assert api.get("/api/painel").json()["pecas"][0]["status"] == "aprovada"
