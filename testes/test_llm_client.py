import httpx
import pytest

# Classes reais que o SDK levanta na Interactions API. Se o SDK mudar esse
# módulo privado, este import quebra e avisa que a classificação precisa de revisão.
from google.genai._gaos.lib import compat_errors as sdk_erros

from src import llm_client
from src.llm_client import (
    AutenticacaoInvalida,
    ChaveAusente,
    ClienteLLM,
    LimiteRequisicoes,
    RequisicaoInvalida,
    RespostaVazia,
    ServicoIndisponivel,
    TempoEsgotado,
    formato_json,
)
from testes.falsos import SDKFalso, interacao

REQUISICAO = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/interactions")
CHAVE_FALSA = "AIza" + "x" * 35


def resposta_http(status):
    return httpx.Response(status, request=REQUISICAO)


def erro_status(classe, status, corpo=None):
    return classe(f"Error code: {status}", response=resposta_http(status), body=corpo)


CORPO_CHAVE_INVALIDA = [
    {"error": {"code": 400, "status": "INVALID_ARGUMENT", "details": [{"reason": "API_KEY_INVALID"}]}}
]


@pytest.mark.parametrize(
    ("erro_sdk", "esperado"),
    [
        (erro_status(sdk_erros.BadRequestError, 400, CORPO_CHAVE_INVALIDA), AutenticacaoInvalida),
        (erro_status(sdk_erros.AuthenticationError, 401), AutenticacaoInvalida),
        (erro_status(sdk_erros.PermissionDeniedError, 403), AutenticacaoInvalida),
        (erro_status(sdk_erros.RateLimitError, 429), LimiteRequisicoes),
        (erro_status(sdk_erros.InternalServerError, 500), ServicoIndisponivel),
        (erro_status(sdk_erros.InternalServerError, 503), ServicoIndisponivel),
        (sdk_erros.APITimeoutError(REQUISICAO), TempoEsgotado),
        (sdk_erros.APIConnectionError(request=REQUISICAO), ServicoIndisponivel),
        (erro_status(sdk_erros.NotFoundError, 404), RequisicaoInvalida),
        (erro_status(sdk_erros.BadRequestError, 400, [{"error": {"status": "INVALID_ARGUMENT"}}]), RequisicaoInvalida),
    ],
)
def test_erros_do_sdk_viram_erros_com_mensagem_para_o_operador(config, erro_sdk, esperado):
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(erro=erro_sdk))
    with pytest.raises(esperado) as capturado:
        cliente.gerar(modelo="gemini-3.8-flash", entrada="oi")
    assert str(capturado.value) == esperado.mensagem_padrao


def test_erro_desconhecido_nao_e_engolido(config):
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(erro=TypeError("bug local")))
    with pytest.raises(TypeError):
        cliente.gerar(modelo="gemini-3.8-flash", entrada="oi")


def test_chave_nao_aparece_no_erro(config):
    vazamento = erro_status(sdk_erros.BadRequestError, 400, f"chave {CHAVE_FALSA} recusada")
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(erro=vazamento))
    with pytest.raises(RequisicaoInvalida) as capturado:
        cliente.gerar(modelo="gemini-3.8-flash", entrada="oi")
    assert CHAVE_FALSA not in str(capturado.value)
    assert CHAVE_FALSA not in capturado.value.detalhe
    assert capturado.value.__cause__ is None


def test_sem_chave_falha_antes_de_chamar(config, monkeypatch):
    monkeypatch.setattr(llm_client, "carregar_chave", lambda: None)
    with pytest.raises(ChaveAusente):
        ClienteLLM(config)


def test_resposta_vazia(config):
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(resposta=interacao("   ")))
    with pytest.raises(RespostaVazia):
        cliente.gerar(modelo="gemini-3.8-flash", entrada="oi")


def test_audio_e_imagem_exigem_o_proprio_conteudo(config):
    com_audio = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(resposta=interacao("", audio="UklGRg==")))
    assert com_audio.gerar(modelo="gemini-3.8-flash-tts", entrada="oi", saida="audio").texto == ""

    so_texto = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(resposta=interacao("desculpe")))
    with pytest.raises(RespostaVazia):
        so_texto.gerar(modelo="gemini-3.8-flash-tts", entrada="oi", saida="audio")
    with pytest.raises(RespostaVazia):
        so_texto.gerar(modelo="gemini-3.1-flash-lite-image", entrada="oi", saida="imagem")
    with pytest.raises(ValueError):
        so_texto.gerar(modelo="gemini-3.8-flash", entrada="oi", saida="video")


def test_imagem_custa_por_unidade(config):
    sdk = SDKFalso(resposta=interacao("", entrada=1000, saida=1290, imagem="iVBORw=="))
    resposta = ClienteLLM(config, chave=CHAVE_FALSA, sdk=sdk).gerar(
        modelo="gemini-3.1-flash-lite-image", entrada="oi", saida="imagem"
    )
    assert resposta.custo_estimado_usd == pytest.approx(1000 * 0.25 / 1_000_000 + 0.0336)


def test_parametros_vem_do_config_e_nao_armazena_no_provedor(config):
    sdk = SDKFalso()
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=sdk)
    resposta = cliente.gerar(
        modelo="gemini-3.8-flash",
        entrada="oi",
        instrucao_sistema="regras",
        formato_resposta=formato_json({"type": "object"}),
        parametros={"seed": 7},
    )
    chamada = sdk.chamadas[0]
    assert chamada["store"] is False
    assert chamada["timeout"] == config.dados["timeout_segundos"]
    assert chamada["generation_config"] == {**config.dados["parametros_geracao"], "seed": 7}
    assert chamada["system_instruction"] == "regras"
    assert chamada["response_format"]["mime_type"] == "application/json"
    assert resposta.parametros["generation_config"]["seed"] == 7
    assert "input" not in resposta.parametros


def test_custo_estimado_conta_raciocinio_como_saida(config):
    sdk = SDKFalso(resposta=interacao("ok", entrada=1000, saida=2000, pensamento=500))
    resposta = ClienteLLM(config, chave=CHAVE_FALSA, sdk=sdk).gerar(modelo="gemini-3.8-flash", entrada="oi")
    assert resposta.tokens_saida == 2500
    assert resposta.custo_estimado_usd == pytest.approx((1000 * 0.75 + 2500 * 3.75) / 1_000_000)


def test_modelo_sem_preco_nao_inventa_custo(config):
    resposta = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso()).gerar(modelo="modelo-sem-preco", entrada="oi")
    assert resposta.custo_estimado_usd is None


def test_cliente_real_so_repete_erro_de_servidor(config, monkeypatch):
    from google import genai

    criados = []
    monkeypatch.setattr(genai, "Client", lambda **kwargs: criados.append(kwargs) or SDKFalso())
    ClienteLLM(config, chave=CHAVE_FALSA)
    assert criados[0]["api_key"] == CHAVE_FALSA
    repeticao = criados[0]["http_options"].retry_options
    assert repeticao.attempts == 1
    assert 429 not in repeticao.http_status_codes and set(repeticao.http_status_codes) == {500, 502, 503, 504}


def test_prazo_de_relogio_independe_do_sdk(config):
    import threading

    liberar = threading.Event()

    class SDKPreso:
        def __init__(self):
            self.interactions = self

        def create(self, **_):
            liberar.wait(5)  # simula o SDK dormindo num Retry-After

    config.dados["timeout_segundos"] = 0.2
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKPreso())
    inicio = __import__("time").perf_counter()
    with pytest.raises(TempoEsgotado):
        cliente.gerar(modelo="gemini-3.8-flash", entrada="oi")
    assert __import__("time").perf_counter() - inicio < 1
    liberar.set()


@pytest.mark.parametrize("status", ["incomplete", "budget_exceeded"])
def test_resposta_cortada_pelo_limite_tem_erro_proprio(config, status):
    from src.llm_client import RespostaIncompleta

    cortada = interacao('{"texto_bruto": "CÓDIGO: 20')
    cortada.status = status
    with pytest.raises(RespostaIncompleta, match="max_output_tokens"):
        ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(resposta=cortada)).gerar(modelo="gemini-3.8-flash", entrada="oi")
