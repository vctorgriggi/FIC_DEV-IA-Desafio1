import json

import pytest

from src.entradas import ArquivoInvalido, validar_arquivo
from src.extracao import CAMPOS_OBRIGATORIOS, NAO_LOCALIZADO, esquema_extracao, normalizar_extracao


def test_valida_arquivo_aceito(config):
    arquivo = validar_arquivo(config.raiz / "dados/originais/entrada_audio.mp3", "audio", config)
    assert arquivo.mime_type == "audio/mp3"
    assert len(arquivo.sha256) == 64


@pytest.mark.parametrize(
    ("nome", "modalidade", "trecho"),
    [
        ("entrada_texto.txt", "audio", "Extensão .txt não aceita"),
        ("inexistente.mp3", "audio", "não encontrado"),
        ("entrada_audio.mp3", "video", "Modalidade desconhecida"),
    ],
)
def test_rejeita_arquivo_invalido(config, nome, modalidade, trecho):
    with pytest.raises(ArquivoInvalido, match=trecho):
        validar_arquivo(config.raiz / "dados/originais" / nome, modalidade, config)


def test_texto_precisa_ser_utf8(config):
    latin1 = config.raiz / "latin1.txt"
    latin1.write_bytes("Solicitação".encode("latin-1"))
    with pytest.raises(ArquivoInvalido, match="UTF-8"):
        validar_arquivo(latin1, "texto", config)


def test_rejeita_arquivo_vazio_e_grande_demais(config):
    vazio = config.raiz / "vazio.mp3"
    vazio.write_bytes(b"")
    with pytest.raises(ArquivoInvalido, match="vazio"):
        validar_arquivo(vazio, "audio", config)

    grande = config.raiz / "grande.mp3"
    grande.write_bytes(b"0" * (2 * 1024 * 1024))
    config.dados["entradas"]["audio"]["tamanho_max_mb"] = 1
    with pytest.raises(ArquivoInvalido, match="limite"):
        validar_arquivo(grande, "audio", config)


def test_extracao_vazia_continua_json_valido_e_pede_revisao():
    campos = normalizar_extracao(None, ["matricula"])
    assert json.loads(json.dumps(campos, ensure_ascii=False)) == campos
    assert all(campos[c] == NAO_LOCALIZADO for c in CAMPOS_OBRIGATORIOS)
    assert campos["categoria"] == NAO_LOCALIZADO
    assert set(campos["campos_ausentes"]) == {*CAMPOS_OBRIGATORIOS, "categoria"}
    assert campos["necessita_revisao"] is True
    assert campos["confianca"] == "baixa"


def test_extracao_completa_preservada():
    dados = {
        "protocolo": "2026-000001",
        "data": "01/10/2026",
        "solicitante": "Pessoa Fictícia",
        "assunto": "Matrícula",
        "pedido": "Lista de documentos",
        "categoria": "matricula",
        "campos_ausentes": [],
        "confianca": "alta",
        "necessita_revisao": False,
        "motivo_revisao": "",
    }
    assert normalizar_extracao(dados, ["matricula"]) == dados


def test_ausencia_forca_revisao_mesmo_se_modelo_disser_que_nao():
    campos = normalizar_extracao({"protocolo": "1", "confianca": "alta", "necessita_revisao": False}, [])
    assert campos["necessita_revisao"] is True
    assert "data" in campos["campos_ausentes"]


def test_categoria_fora_da_lista_vira_nao_localizado():
    assert normalizar_extracao({"categoria": "inventada"}, ["matricula"])["categoria"] == NAO_LOCALIZADO


def test_esquema_exige_todos_os_campos_e_limita_categorias():
    esquema = esquema_extracao(["matricula"])
    assert set(esquema["required"]) == set(esquema["properties"])
    assert esquema["properties"]["categoria"]["enum"] == ["matricula", NAO_LOCALIZADO]
