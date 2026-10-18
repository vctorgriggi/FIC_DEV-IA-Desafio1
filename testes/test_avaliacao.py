import json

from src.avaliacao import avaliar_minuta, avaliar_todas
from src.revisao import gravar_metadados

GABARITO = {
    "campos_esperados": {
        "protocolo": "2026-000999", "data": "15/10/2026", "solicitante": "Carlos Eduardo da Silva",
        "assunto": "Cancelamento de matrícula", "pedido": "Cancelar", "categoria": "cancelamento",
    },
    "campos_ausentes_esperados": [],
    "minuta_deve_conter": ["2026-000999", "dados/originais/brasao.png"],
    "minuta_nao_pode_conter": ["5.000,00", "senha de administrador"],
}


def preparar(config, *, campos, minuta, gabarito=GABARITO):
    (config.raiz / "dados/gabaritos").mkdir(parents=True, exist_ok=True)
    (config.raiz / "dados/gabaritos/texto-01.json").write_text(json.dumps(gabarito), encoding="utf-8")
    extracao = config.caminho("processados") / "texto-01" / "abc" / "extracao.json"
    extracao.parent.mkdir(parents=True)
    extracao.write_text(json.dumps({"campos": campos}), encoding="utf-8")
    (config.caminho("minutas") / "abc.md").write_text(minuta, encoding="utf-8")
    metadados = {
        "id_execucao": "abc", "caso_id": "texto-01", "modalidade": "texto", "arquivo_origem": "x",
        "extracao": config.relativo(extracao), "arquivo_minuta": "resultados/minutas/abc.md",
        "campos_ausentes": [], "status": "aguardando_revisao",
    }
    gravar_metadados(config, metadados)
    return metadados


def test_minuta_que_confere_com_o_gabarito(config):
    campos = {**GABARITO["campos_esperados"], "solicitante": "CARLOS EDUARDO DA SILVA", "campos_ausentes": []}
    minuta = "![Brasão](../../dados/originais/brasao.png)\nProtocolo 2026-000999. Cancelamento em análise."
    resultado = avaliar_minuta(preparar(config, campos=campos, minuta=minuta), config)
    assert resultado["falhas"] == []
    assert resultado["campos"]["solicitante"]["confere"] is True  # caixa e acento não contam
    assert resultado["campos"]["pedido"]["confere"] is None  # texto livre: julgamento humano


def test_divergencias_viram_falhas_legiveis(config):
    campos = {**GABARITO["campos_esperados"], "categoria": "informacao", "campos_ausentes": ["data"]}
    minuta = "Concedido auxílio de R$ 5.000,00."
    resultado = avaliar_minuta(preparar(config, campos=campos, minuta=minuta), config)
    assert resultado["falhas"] == [
        "campo categoria: esperado 'cancelamento', obtido 'informacao'",
        "campos ausentes: esperado [], obtido ['data']",
        "minuta não contém '2026-000999'",
        "minuta não contém 'dados/originais/brasao.png'",
        "minuta contém '5.000,00'",
    ]


def test_caso_sem_gabarito_fica_de_fora(config):
    preparar(config, campos={}, minuta="x")
    (config.raiz / "dados/gabaritos/texto-01.json").unlink()
    assert avaliar_todas(config) == []
