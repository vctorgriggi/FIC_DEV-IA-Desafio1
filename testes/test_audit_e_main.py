import json

import pytest

from src import main as cli
from src.audit import Auditoria, Evento
from src.llm_client import RespostaLLM


def test_evento_tem_campos_fixos_e_oculta_segredo(config):
    auditoria = Auditoria(config, segredos=["segredo-123"])
    resposta = RespostaLLM(
        texto="x", modelo="gpt-6.1-terra", duracao_s=1.2, tokens_entrada=3, tokens_saida=4,
        custo_estimado_usd=0.001, parametros={"store": False},
    )
    auditoria.registrar(Evento(id_execucao="e1", caso_id="texto-01", etapa="compreensao", erro="falhou com segredo-123").com_resposta(resposta))

    linha = auditoria.arquivo.read_text(encoding="utf-8")
    assert "segredo-123" not in linha
    registro = json.loads(linha)
    assert registro["provedor"] == "openai"
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
    assert ambiente["versoes"]["openai"] != "não instalada"
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


def test_revisar_com_correcao_le_o_texto_de_um_arquivo(cli_isolada, monkeypatch, tmp_path):
    from src.minuta import cabecalho
    from src.revisao import gravar_metadados

    campos = {"protocolo": "2026-000001", "data": "01/10/2026", "solicitante": "Fulano", "assunto": "Matrícula"}
    extracao = cli_isolada.raiz / "dados/processados/extracao.json"
    extracao.write_text(json.dumps({"campos": campos}), encoding="utf-8")
    topo = cabecalho(campos, cli_isolada)
    (cli_isolada.caminho("minutas") / "abc.md").write_text(f"{topo}\n\nCorpo do modelo.\n", encoding="utf-8")
    gravar_metadados(cli_isolada, {
        "id_execucao": "abc", "caso_id": "texto-01", "modalidade": "texto", "arquivo_origem": "x",
        "extracao": "dados/processados/extracao.json", "arquivo_minuta": "resultados/minutas/abc.md",
        "campos_ausentes": [], "status": "aguardando_revisao",
    })
    corrigido = tmp_path / "corrigido.md"
    corrigido.write_text(f"{topo}\n\nCorpo corrigido.", encoding="utf-8")
    respostas = iter(["c", "Corrigi o corpo.", "Servidor A", str(corrigido)])
    monkeypatch.setattr("builtins.input", lambda _: next(respostas))

    assert cli.main(["revisar", "abc"]) == 0
    assert (cli_isolada.caminho("minutas") / "abc.md").read_text(encoding="utf-8").endswith("Corpo corrigido.\n")
    assert (cli_isolada.caminho("minutas") / "abc_gerada.md").read_text(encoding="utf-8").endswith("Corpo do modelo.\n")
