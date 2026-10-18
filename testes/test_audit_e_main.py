import json

import pytest

from src import main as cli
from src.audit import Auditoria, Evento
from src.llm_client import RespostaLLM


def test_evento_tem_campos_fixos_e_oculta_segredo(config):
    auditoria = Auditoria(config, segredos=["segredo-123"])
    resposta = RespostaLLM(
        texto="x", modelo="gemini-3.8-flash", duracao_s=1.2, tokens_entrada=3, tokens_saida=4,
        custo_estimado_usd=0.001, parametros={"store": False},
    )
    auditoria.registrar(Evento(id_execucao="e1", caso_id="texto-01", etapa="compreensao", erro="falhou com segredo-123").com_resposta(resposta))

    linha = auditoria.arquivo.read_text(encoding="utf-8")
    assert "segredo-123" not in linha
    registro = json.loads(linha)
    assert registro["provedor"] == "gemini"
    assert registro["parametros"] == {"store": False}
    assert {"id_evento", "data_hora", "versao_prompt", "decisao_humana", "custo_estimado_usd"} <= set(registro)
    assert auditoria.eventos(caso_id="texto-01")[0]["id_execucao"] == "e1"


@pytest.fixture
def cli_isolada(config, monkeypatch):
    monkeypatch.setattr(cli, "carregar_config", lambda: config)
    monkeypatch.setattr(cli, "carregar_chave", lambda: None)
    monkeypatch.setattr("src.llm_client.carregar_chave", lambda: None)
    monkeypatch.setattr("src.audit.carregar_chave", lambda: None)
    return config


def test_verificar_registra_versoes_sem_chamar_api(cli_isolada, capsys):
    assert cli.main(["verificar"]) == 0
    ambiente = json.loads((cli_isolada.caminho("logs") / "ambiente.json").read_text(encoding="utf-8"))
    assert ambiente["versoes"]["google-genai"] != "não instalada"
    assert ambiente["chave_configurada"] is False
    assert "AUSENTE" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argumentos", "codigo"),
    [
        (["casos"], 0),
        (["processar", "nao-existe"], cli.SAIDA_ERRO_USO),
        (["processar", "texto-01"], cli.SAIDA_ERRO_PROVEDOR),
        (["revisar", "id-inexistente"], cli.SAIDA_ERRO_USO),
    ],
)
def test_codigos_de_saida(cli_isolada, argumentos, codigo):
    assert cli.main(argumentos) == codigo


def test_parte_pendente_tem_codigo_proprio(cli_isolada, monkeypatch):
    from testes.falsos import SDKFalso
    from src.tipos import PendenteDeImplementacao

    def pendente(*args, **kwargs):
        raise PendenteDeImplementacao("RF06", "teste simulado")

    monkeypatch.setattr(cli, "ClienteLLM", lambda config: SDKFalso())
    monkeypatch.setattr(cli.fluxo.audio, "transcrever", pendente)
    assert cli.main(["processar", "audio-01"]) == cli.SAIDA_PENDENTE



def test_avaliacao_sem_revisoes(cli_isolada, capsys):
    assert cli.main(["avaliacao"]) == 0
    assert "Nenhuma minuta revisada" in capsys.readouterr().out


def test_especificacao_invalida_e_erro_de_uso(cli_isolada):
    assert cli.main(["peca-visual", "texto-01", "--especificacao", "nao-existe.json"]) == cli.SAIDA_ERRO_USO


def test_cancelar_revisao_nao_registra_decisao(cli_isolada, monkeypatch):
    from src.revisao import gravar_metadados

    (cli_isolada.caminho("minutas") / "abc.md").write_text("Minuta", encoding="utf-8")
    gravar_metadados(cli_isolada, {
        "id_execucao": "abc", "caso_id": "texto-01", "modalidade": "texto", "arquivo_origem": "x",
        "arquivo_minuta": "resultados/minutas/abc.md", "campos_ausentes": [], "status": "aguardando_revisao",
    })

    def cancelar(_):
        raise EOFError

    monkeypatch.setattr("builtins.input", cancelar)
    assert cli.main(["revisar", "abc"]) == cli.SAIDA_CANCELADA
    assert json.loads((cli_isolada.caminho("minutas") / "abc.json").read_text(encoding="utf-8"))["status"] == "aguardando_revisao"
