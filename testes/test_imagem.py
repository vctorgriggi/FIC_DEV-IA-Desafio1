"""RF08 (visão/OCR) e RF10 (peça visual), com o SDK falso."""

import base64
import io
import json
from types import SimpleNamespace

import pytest
from PIL import Image

from src import fluxo, image_generation
from src.comparacao import comparar_com_gabarito, comparar_texto, conferir_dados_criticos, tokens
from src.config import RAIZ
from src.entradas import validar_arquivo
from src.image_generation import ErroPeca, PecaVisual, gerar_peca, montar_prompt, validar_especificacao
from src.llm_client import ClienteLLM, RespostaMalformada, RespostaVazia
from src.revisao import CHECKLIST_PECA, RevisaoInvalida, registrar_revisao_peca
from src.tipos import PendenteDeImplementacao
from src.vision import extrair_texto
from testes.falsos import SDKFalso, interacao

ESPECIFICACAO = json.loads((RAIZ / "prompts/peca_visual_v1.json").read_text(encoding="utf-8"))
RESPOSTA_OCR = {
    "texto_bruto": "CÓDIGO: 2024-000142\nNOME: MARCOS VINICIUS",
    "texto_revisado": "CÓDIGO: 2024-000142\nNOME: MARCOS VINÍCIUS",
    "trechos_incertos": [{"trecho": "2024", "motivo": "dígito rasurado"}, {"trecho": " ", "motivo": "vazio"}],
    "legibilidade": "regular",
    "observacoes": "",
}


def cliente_com(config, resposta):
    return ClienteLLM(config, chave="chave-teste", sdk=SDKFalso(resposta=resposta))


def png_base64(largura=400, altura=500):
    buffer = io.BytesIO()
    Image.new("RGB", (largura, altura), "#88aacc").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


# --- RF08 -------------------------------------------------------------------


def test_ocr_envia_pdf_como_documento_e_separa_bruto_revisado_incerto(config):
    arquivo = validar_arquivo(config.raiz / "dados/originais/entrada_pdf-imagem.pdf", "imagem", config)
    sdk = SDKFalso(resposta=interacao(json.dumps(RESPOSTA_OCR)))
    extraido = extrair_texto(arquivo, cliente=ClienteLLM(config, chave="chave-teste", sdk=sdk), config=config)

    chamada = sdk.chamadas[0]
    assert chamada["model"] == config.modelo("visao")
    assert chamada["input"][1]["type"] == "document"
    assert chamada["input"][1]["mime_type"] == "application/pdf"
    assert "<conteudo_externo>" in chamada["system_instruction"]
    assert chamada["response_format"]["mime_type"] == "application/json"

    assert extraido.texto_bruto == RESPOSTA_OCR["texto_bruto"]
    assert extraido.texto_revisado.endswith("VINÍCIUS")
    assert extraido.trechos_incertos == ["2024 — dígito rasurado"]
    assert extraido.metadados["legibilidade"] == "regular"
    assert extraido.metadados["sha256_original"] == arquivo.sha256
    assert extraido.prompt.identificador == "ocr_v1"


def test_ocr_de_foto_envia_como_imagem(config):
    foto = config.raiz / "foto.png"
    foto.write_bytes(base64.b64decode(png_base64(10, 10)))
    sdk = SDKFalso(resposta=interacao(json.dumps(RESPOSTA_OCR)))
    extrair_texto(validar_arquivo(foto, "imagem", config), cliente=ClienteLLM(config, chave="c", sdk=sdk), config=config)
    assert sdk.chamadas[0]["input"][1]["type"] == "image"


@pytest.mark.parametrize(
    ("texto", "erro"),
    [("isto não é json", RespostaMalformada), ("[1, 2]", RespostaMalformada), (json.dumps({"texto_bruto": " "}), RespostaVazia)],
)
def test_ocr_sem_texto_ou_fora_do_formato_falha(config, texto, erro):
    arquivo = validar_arquivo(config.raiz / "dados/originais/entrada_pdf-imagem.pdf", "imagem", config)
    with pytest.raises(erro):
        extrair_texto(arquivo, cliente=cliente_com(config, interacao(texto)), config=config)


def test_tokens_ignoram_caixa_e_acento_mas_preservam_dados():
    assert tokens("NOME: Vinícius; CPF: 123.456.789-00, e-mail: A.B@X.COM.") == [
        "nome", "vinicius", "cpf", "123.456.789-00", "e-mail", "a.b@x.com"
    ]


def test_comparacao_aponta_substituicao_omissao_e_insercao():
    resultado = comparar_texto("codigo 2024-000142 nome marcos extra", "CÓDIGO: 2026-000142 NOME: MARCOS VINICIUS")
    tipos = {(e["tipo"], e["esperado"], e["obtido"]) for e in resultado["erros"]}
    assert ("substituicao", "2026-000142", "2024-000142") in tipos
    assert ("substituicao", "vinicius", "extra") in tipos
    assert resultado["palavras_referencia"] == 5
    assert resultado["palavras_corretas"] == 3
    assert comparar_texto("a c", "a b c")["erros"] == [{"tipo": "omissao", "esperado": "b", "obtido": ""}]
    assert comparar_texto("a b x c", "a b c")["erros"] == [{"tipo": "insercao", "esperado": "", "obtido": "x"}]
    assert comparar_texto("A b", "a B")["similaridade"] == 1.0


def test_dados_criticos_e_gabarito_sem_referencia():
    conferencia = conferir_dados_criticos("CPF 123.456.789-00 nome Marcos Vinícius", ["123.456.789-00", "MARCOS VINICIUS", "1234567-8"])
    assert conferencia == {"encontrados": ["123.456.789-00", "MARCOS VINICIUS"], "nao_encontrados": ["1234567-8"]}
    assert comparar_com_gabarito("x", "x", {"texto_referencia": " "}) is None


def test_gabarito_imagem_coerente_com_os_dados_criticos():
    gabarito = json.loads((RAIZ / "dados/gabaritos/imagem-01.json").read_text(encoding="utf-8"))
    conferencia = conferir_dados_criticos(gabarito["texto_referencia"], gabarito["dados_criticos"])
    assert conferencia["nao_encontrados"] == []


def test_fluxo_imagem_compara_com_gabarito_antes_da_compreensao(config, auditoria):
    gabarito = {"texto_referencia": "CÓDIGO: 2026-000142\nNOME: MARCOS VINICIUS", "dados_criticos": ["2026-000142"]}
    (config.raiz / "dados/gabaritos").mkdir(parents=True)
    (config.raiz / "dados/gabaritos/imagem-01.json").write_text(json.dumps(gabarito), encoding="utf-8")

    cliente = cliente_com(config, interacao(json.dumps(RESPOSTA_OCR)))
    with pytest.raises(PendenteDeImplementacao, match="RF05"):
        fluxo.processar_caso("imagem-01", config=config, cliente=cliente, auditoria=auditoria)

    eventos = auditoria.eventos(caso_id="imagem-01")
    assert [e["etapa"] for e in eventos] == ["entrada", "extracao_texto", "comparacao_gabarito", "compreensao"]
    comparacao = eventos[2]
    assert comparacao["extra"]["dados_criticos_nao_encontrados"] == ["2026-000142"]
    pasta = config.raiz / comparacao["saida"].rsplit("/", 1)[0]
    assert (pasta / "texto_bruto.txt").read_text(encoding="utf-8") == RESPOSTA_OCR["texto_bruto"]
    assert json.loads((pasta / "comparacao_gabarito.json").read_text(encoding="utf-8"))["bruto"]["erros"]
    assert eventos[1]["versao_prompt"] == "ocr_v1"


# --- RF10 -------------------------------------------------------------------


def test_especificacao_versionada_e_valida():
    validar_especificacao(ESPECIFICACAO)


@pytest.mark.parametrize(
    ("alteracao", "trecho"),
    [
        ({"sujeito": ""}, "sujeito"),
        ({"proporcao": "7:3"}, "Proporção"),
        ({"restricoes": "sem texto"}, "lista"),
        ({"texto": {"itens": []}}, "titulo"),
    ],
)
def test_especificacao_invalida(alteracao, trecho):
    with pytest.raises(ErroPeca, match=trecho):
        validar_especificacao({**ESPECIFICACAO, **alteracao})


def test_prompt_tem_os_campos_e_as_restricoes_obrigatorias_sem_repetir():
    especificacao = {**ESPECIFICACAO, "restricoes": [image_generation.RESTRICOES_OBRIGATORIAS[0], "extra"]}
    prompt = montar_prompt(especificacao, edicao=False)
    for rotulo in ("Sujeito:", "Composição:", "Estilo:", "Iluminação:", f"Proporção: {ESPECIFICACAO['proporcao']}", "Restrições:"):
        assert rotulo in prompt
    for restricao in image_generation.RESTRICOES_OBRIGATORIAS:
        assert prompt.count(restricao) == 1
    assert prompt.startswith("Gere") and montar_prompt(ESPECIFICACAO, edicao=True).startswith("Edite")


def test_gera_peca_com_texto_e_selo_e_preserva_a_ilustracao_original(config):
    dados = png_base64()
    sdk = SDKFalso(resposta=interacao("", imagem=dados))
    destino = config.caminho("imagens") / "abc.png"
    peca = gerar_peca(ESPECIFICACAO, destino, imagem_base=None, cliente=ClienteLLM(config, chave="c", sdk=sdk), config=config)

    formato = sdk.chamadas[0]["response_format"]
    assert formato == {"type": "image", "aspect_ratio": ESPECIFICACAO["proporcao"], "image_size": "1K"}
    assert sdk.chamadas[0]["model"] == config.modelo("imagem")
    assert peca.ilustracao_original.read_bytes() == base64.b64decode(dados)
    with Image.open(peca.caminho) as final:
        assert final.width == image_generation.LARGURA_PECA
        assert final.height > image_generation.LARGURA_PECA * 500 / 400  # ilustração + painel de texto
    assert "gerada por IA" in peca.nota_proveniencia and config.modelo("imagem") in peca.nota_proveniencia
    assert peca.prompt == montar_prompt(ESPECIFICACAO, edicao=False)


def test_edicao_envia_a_imagem_base_e_recusa_pdf(config):
    base = config.raiz / "base.png"
    base.write_bytes(base64.b64decode(png_base64(20, 20)))
    sdk = SDKFalso(resposta=interacao("", imagem=png_base64()))
    cliente = ClienteLLM(config, chave="c", sdk=sdk)
    peca = gerar_peca(ESPECIFICACAO, config.caminho("imagens") / "e.png", imagem_base=base, cliente=cliente, config=config)
    assert sdk.chamadas[0]["input"][1] == {"type": "image", "data": png_base64(20, 20), "mime_type": "image/png"}
    assert "editada" in peca.nota_proveniencia

    with pytest.raises(ErroPeca, match="Só imagem"):
        gerar_peca(ESPECIFICACAO, config.caminho("imagens") / "f.png",
                   imagem_base=config.raiz / "dados/originais/entrada_pdf-imagem.pdf", cliente=cliente, config=config)


def test_sem_fonte_com_acento_para_em_vez_de_quebrar_o_texto(config, monkeypatch):
    monkeypatch.setattr(image_generation, "FONTES", {False: ("/nao/existe.ttf",), True: ("/nao/existe.ttf",)})
    sdk = SDKFalso(resposta=interacao("", imagem=png_base64()))
    with pytest.raises(ErroPeca, match="fonte"):
        gerar_peca(ESPECIFICACAO, config.caminho("imagens") / "g.png", imagem_base=None,
                   cliente=ClienteLLM(config, chave="c", sdk=sdk), config=config)


@pytest.fixture
def peca_gerada(config, auditoria):
    sdk = SDKFalso(resposta=interacao("", imagem=png_base64()))
    peca = fluxo.gerar_peca_visual(
        "imagem-01", ESPECIFICACAO, imagem_base=None, config=config,
        cliente=ClienteLLM(config, chave="c", sdk=sdk), auditoria=auditoria,
    )
    return peca.caminho.stem


def test_fluxo_grava_metadados_aguardando_revisao(config, peca_gerada):
    metadados = json.loads((config.caminho("imagens") / f"{peca_gerada}.json").read_text(encoding="utf-8"))
    assert metadados["status"] == "aguardando_revisao"
    assert metadados["ilustracao_original"].endswith("_ilustracao_ia.png")
    assert metadados["modelo"] == config.modelo("imagem")


def test_revisao_da_peca_exige_checklist_completo_para_aprovar(config, auditoria, peca_gerada):
    tudo_ok = {chave: True for chave in CHECKLIST_PECA}
    with pytest.raises(RevisaoInvalida, match="textos"):
        registrar_revisao_peca(config, auditoria, peca_gerada, checklist={**tudo_ok, "textos": False},
                               decisao="aprovar", justificativa="ok", revisor="Servidor A")
    with pytest.raises(RevisaoInvalida, match="checklist"):
        registrar_revisao_peca(config, auditoria, peca_gerada, checklist={"textos": True},
                               decisao="aprovar", justificativa="ok", revisor="Servidor A")

    metadados = registrar_revisao_peca(config, auditoria, peca_gerada, checklist=tudo_ok,
                                       decisao="aprovar", justificativa="Conferida", revisor="Servidor A")
    assert metadados["status"] == "aprovada"
    assert len(metadados["revisao"]["sha256_peca"]) == 64
    assert auditoria.eventos(etapa="revisao_peca")[0]["extra"]["checklist"] == tudo_ok
    with pytest.raises(RevisaoInvalida, match="já foi revisada"):
        registrar_revisao_peca(config, auditoria, peca_gerada, checklist=tudo_ok,
                               decisao="rejeitar", justificativa="x", revisor="Servidor A")


def test_peca_com_item_reprovado_pode_ser_rejeitada(config, auditoria, peca_gerada):
    checklist = {chave: chave != "textos" for chave in CHECKLIST_PECA}
    metadados = registrar_revisao_peca(config, auditoria, peca_gerada, checklist=checklist,
                                       decisao="nova_geracao", justificativa="Letra deformada", revisor="Servidor A")
    assert metadados["status"] == "nova_geracao_solicitada"
