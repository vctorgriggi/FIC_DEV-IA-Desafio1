import base64

import httpx2
import openai
import pytest

from src import llm_client
from src.llm_client import (
    AutenticacaoInvalida,
    ChaveAusente,
    ClienteLLM,
    LimiteRequisicoes,
    RequisicaoInvalida,
    RespostaIncompleta,
    RespostaVazia,
    ServicoIndisponivel,
    TempoEsgotado,
    entrada_com_anexo,
    formato_json,
)
from testes.falsos import SDKFalso, audio, imagem, resposta, transcricao

REQUISICAO = httpx2.Request("POST", "https://api.openai.com/v1/responses")
CHAVE_FALSA = "sk-proj-" + "x" * 40


def erro_status(classe, status, corpo=None):
    return classe(f"Error code: {status}", response=httpx2.Response(status, request=REQUISICAO), body=corpo)


@pytest.mark.parametrize(
    ("erro_sdk", "esperado"),
    [
        (erro_status(openai.AuthenticationError, 401), AutenticacaoInvalida),
        (erro_status(openai.PermissionDeniedError, 403), AutenticacaoInvalida),
        (erro_status(openai.RateLimitError, 429), LimiteRequisicoes),
        (erro_status(openai.InternalServerError, 500), ServicoIndisponivel),
        (erro_status(openai.InternalServerError, 503), ServicoIndisponivel),
        (openai.APITimeoutError(REQUISICAO), TempoEsgotado),
        (openai.APIConnectionError(request=REQUISICAO), ServicoIndisponivel),
        (erro_status(openai.NotFoundError, 404), RequisicaoInvalida),
        (erro_status(openai.BadRequestError, 400), RequisicaoInvalida),
    ],
)
def test_erros_do_sdk_viram_erros_com_mensagem_para_o_operador(config, erro_sdk, esperado):
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(erro=erro_sdk))
    with pytest.raises(esperado) as capturado:
        cliente.gerar(modelo="gpt-6.1-terra", entrada="oi")
    assert str(capturado.value) == esperado.mensagem_padrao


def test_erros_valem_para_todas_as_operacoes(config):
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(erro=erro_status(openai.RateLimitError, 429)))
    with pytest.raises(LimiteRequisicoes):
        cliente.transcrever(modelo="gpt-transcribe", nome_arquivo="a.mp3", conteudo=b"x", mime_type="audio/mp3")
    with pytest.raises(LimiteRequisicoes):
        cliente.sintetizar_voz(modelo="gpt-4o-mini-tts", texto="oi", voz="marin", instrucoes="calmo")
    with pytest.raises(LimiteRequisicoes):
        cliente.gerar_imagem(modelo="gpt-image-2.5-flare", prompt="oi", tamanho="1024x1024")


def test_erro_desconhecido_nao_e_engolido(config):
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(erro=TypeError("bug local")))
    with pytest.raises(TypeError):
        cliente.gerar(modelo="gpt-6.1-terra", entrada="oi")


def test_chave_nao_aparece_no_erro(config):
    vazamento = erro_status(openai.BadRequestError, 400, f"chave {CHAVE_FALSA} recusada")
    vazamento.args = (f"Error code: 400 - chave {CHAVE_FALSA} recusada",)
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(erro=vazamento))
    with pytest.raises(RequisicaoInvalida) as capturado:
        cliente.gerar(modelo="gpt-6.1-terra", entrada="oi")
    assert CHAVE_FALSA not in str(capturado.value)
    assert CHAVE_FALSA not in capturado.value.detalhe
    assert capturado.value.__cause__ is None


def test_sem_chave_falha_antes_de_chamar(config, monkeypatch):
    monkeypatch.setattr(llm_client, "carregar_chave", lambda: None)
    with pytest.raises(ChaveAusente):
        ClienteLLM(config)


def test_resposta_vazia(config):
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(resposta("   ")))
    with pytest.raises(RespostaVazia):
        cliente.gerar(modelo="gpt-6.1-terra", entrada="oi")


def test_audio_e_imagem_exigem_o_proprio_conteudo(config):
    vazio = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(audio(b"")))
    with pytest.raises(RespostaVazia):
        vazio.sintetizar_voz(modelo="gpt-4o-mini-tts", texto="oi", voz="marin", instrucoes="calmo")
    sem_imagem = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(imagem(None)))
    with pytest.raises(RespostaVazia):
        sem_imagem.gerar_imagem(modelo="gpt-image-2.5-flare", prompt="oi", tamanho="1024x1024")
    sem_fala = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(transcricao("  ")))
    with pytest.raises(RespostaVazia):
        sem_fala.transcrever(modelo="gpt-transcribe", nome_arquivo="a.mp3", conteudo=b"x", mime_type="audio/mp3")


def test_parametros_vem_do_config_e_nao_armazena_no_provedor(config):
    sdk = SDKFalso()
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=sdk)
    obtida = cliente.gerar(
        modelo="gpt-6.1-terra",
        entrada="oi",
        instrucao_sistema="regras",
        formato_resposta=formato_json({"type": "object"}, "teste"),
        parametros={"reasoning": {"effort": "low"}},
    )
    chamada = sdk.chamadas[0]
    assert chamada["_operacao"] == "responses.create"
    assert chamada["store"] is False
    assert chamada["timeout"] == config.dados["timeout_segundos"]
    assert chamada["max_output_tokens"] == config.dados["parametros_geracao"]["max_output_tokens"]
    assert chamada["reasoning"] == {"effort": "low"}
    assert chamada["instructions"] == "regras"
    assert chamada["text"]["format"]["type"] == "json_schema"
    assert obtida.parametros["reasoning"] == {"effort": "low"}
    assert obtida.parametros["formato_resposta"] == "teste"
    assert "input" not in obtida.parametros


def test_formato_json_estrito_fecha_todos_os_objetos():
    esquema = {
        "type": "object",
        "properties": {"lista": {"type": "array", "items": {"type": "object", "properties": {"a": {"type": "string"}}}}},
    }
    formato = formato_json(esquema, "teste")["format"]
    assert formato["strict"] is True
    assert formato["schema"]["additionalProperties"] is False
    assert formato["schema"]["properties"]["lista"]["items"]["additionalProperties"] is False
    assert "additionalProperties" not in esquema


def test_anexo_pdf_vai_como_arquivo_e_imagem_como_imagem():
    pdf = entrada_com_anexo("leia", nome_arquivo="ficha.pdf", mime_type="application/pdf", conteudo=b"%PDF")
    partes = pdf[0]["content"]
    assert partes[0] == {"type": "input_text", "text": "leia"}
    assert partes[1]["type"] == "input_file" and partes[1]["filename"] == "ficha.pdf"
    assert partes[1]["file_data"] == "data:application/pdf;base64," + base64.b64encode(b"%PDF").decode()
    png = entrada_com_anexo("leia", nome_arquivo="f.png", mime_type="image/png", conteudo=b"PNG")
    assert png[0]["content"][1] == {"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(b"PNG").decode()}


def test_custo_estimado_de_texto(config):
    sdk = SDKFalso(resposta("ok", entrada=1000, saida=2500))
    obtida = ClienteLLM(config, chave=CHAVE_FALSA, sdk=sdk).gerar(modelo="gpt-6.1-terra", entrada="oi")
    assert obtida.tokens_saida == 2500
    assert obtida.custo_estimado_usd == pytest.approx((1000 * 1.0 + 2500 * 5.0) / 1_000_000)


def test_modelo_sem_preco_nao_inventa_custo(config):
    obtida = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso()).gerar(modelo="modelo-sem-preco", entrada="oi")
    assert obtida.custo_estimado_usd is None


def test_transcricao_custa_por_minuto_e_repassa_idiomas(config):
    sdk = SDKFalso(transcricao("Bom dia", segundos=120))
    obtida = ClienteLLM(config, chave=CHAVE_FALSA, sdk=sdk).transcrever(
        modelo="gpt-transcribe", nome_arquivo="a.mp3", conteudo=b"ID3", mime_type="audio/mp3", idiomas=["pt"]
    )
    chamada = sdk.chamadas[0]
    assert chamada["_operacao"] == "audio.transcriptions.create"
    assert chamada["file"] == ("a.mp3", b"ID3", "audio/mp3")
    assert chamada["languages"] == ["pt"]
    assert "store" not in chamada
    assert obtida.texto == "Bom dia"
    assert obtida.custo_estimado_usd == pytest.approx(2 * 0.0045)


def test_sintese_pede_wav_com_voz_e_instrucoes(config):
    sdk = SDKFalso(audio(b"RIFF"))
    obtida = ClienteLLM(config, chave=CHAVE_FALSA, sdk=sdk).sintetizar_voz(
        modelo="gpt-4o-mini-tts", texto="Prezado", voz="marin", instrucoes="tom institucional"
    )
    chamada = sdk.chamadas[0]
    assert chamada["_operacao"] == "audio.speech.create"
    assert (chamada["input"], chamada["voice"], chamada["instructions"], chamada["response_format"]) == (
        "Prezado", "marin", "tom institucional", "wav"
    )
    assert obtida.conteudo == b"RIFF" and obtida.custo_estimado_usd is None


def test_imagem_gerada_ou_editada_com_custo_por_token(config):
    b64 = base64.b64encode(b"PNG").decode()
    sdk = SDKFalso(imagem(b64, texto=100, imagem_entrada=200, saida=1000))
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=sdk)
    gerada = cliente.gerar_imagem(modelo="gpt-image-2.5-flare", prompt="cartaz", tamanho="1536x1152")
    assert gerada.conteudo == b"PNG"
    assert gerada.custo_estimado_usd == pytest.approx((100 * 5.0 + 200 * 8.0 + 1000 * 30.0) / 1_000_000)
    cliente.gerar_imagem(modelo="gpt-image-2.5-flare", prompt="cartaz", tamanho="1024x1024", imagem_base=("b.png", b"x", "image/png"))
    assert [c["_operacao"] for c in sdk.chamadas] == ["images.generate", "images.edit"]
    assert sdk.chamadas[0]["size"] == "1536x1152" and "image" not in sdk.chamadas[0]
    assert sdk.chamadas[1]["image"] == ("b.png", b"x", "image/png")


def test_imagem_sem_uso_informado_fica_sem_custo(config):
    sdk = SDKFalso(imagem(base64.b64encode(b"PNG").decode()))
    obtida = ClienteLLM(config, chave=CHAVE_FALSA, sdk=sdk).gerar_imagem(
        modelo="gpt-image-2.5-flare", prompt="cartaz", tamanho="1024x1024"
    )
    assert obtida.custo_estimado_usd is None


def test_cliente_real_nao_repete_chamadas(config, monkeypatch):
    criados = []
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: criados.append(kwargs) or SDKFalso())
    ClienteLLM(config, chave=CHAVE_FALSA)
    assert criados[0]["api_key"] == CHAVE_FALSA
    assert criados[0]["max_retries"] == 0


def test_prazo_de_relogio_independe_do_sdk(config):
    import threading
    import time
    from types import SimpleNamespace

    liberar = threading.Event()

    def preso(**_):
        liberar.wait(5)  # simula o SDK preso numa conexão lenta

    config.dados["timeout_segundos"] = 0.2
    cliente = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SimpleNamespace(responses=SimpleNamespace(create=preso)))
    inicio = time.perf_counter()
    with pytest.raises(TempoEsgotado):
        cliente.gerar(modelo="gpt-6.1-terra", entrada="oi")
    assert time.perf_counter() - inicio < 1
    liberar.set()


def test_resposta_cortada_pelo_limite_tem_erro_proprio(config):
    cortada = resposta('{"texto_bruto": "CÓDIGO: 20', status="incomplete", motivo="max_output_tokens")
    with pytest.raises(RespostaIncompleta, match="max_output_tokens"):
        ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(cortada)).gerar(modelo="gpt-6.1-terra", entrada="oi")


def test_resposta_incompleta_por_outro_motivo_diz_o_motivo(config):
    filtrada = resposta("parcial", status="incomplete", motivo="content_filter")
    with pytest.raises(RespostaIncompleta, match="content_filter"):
        ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(filtrada)).gerar(modelo="gpt-6.1-terra", entrada="oi")


def test_resposta_com_falha_do_provedor(config):
    falhou = resposta("", status="failed")
    with pytest.raises(ServicoIndisponivel):
        ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(falhou)).gerar(modelo="gpt-6.1-terra", entrada="oi")


def _wav(frames=b"\x00\x01" * 2400):
    import io
    import wave

    destino = io.BytesIO()
    with wave.open(destino, "wb") as w:
        w.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        w.writeframes(frames)
    return destino.getvalue()


def test_wav_em_streaming_ganha_os_tamanhos_reais(config):
    from src.audio import validar_wav

    completo = _wav()
    # Como a Speech API devolve: RIFF e data com tamanho 0xFFFFFFFF.
    streaming = completo[:4] + b"\xff\xff\xff\xff" + completo[8:40] + b"\xff\xff\xff\xff" + completo[44:]
    obtida = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(audio(streaming))).sintetizar_voz(
        modelo="gpt-4o-mini-tts", texto="oi", voz="marin", instrucoes="calmo"
    )
    assert obtida.conteudo == completo
    assert validar_wav(obtida.conteudo)["duracao_audio_s"] == 0.1


def test_wav_com_tamanhos_ou_quebrado_nao_e_alterado(config):
    completo = _wav()
    so_riff = completo[:4] + b"\xff\xff\xff\xff" + completo[8:]
    for conteudo in (completo, so_riff, b"RIFF invalido"):
        obtida = ClienteLLM(config, chave=CHAVE_FALSA, sdk=SDKFalso(audio(conteudo))).sintetizar_voz(
            modelo="gpt-4o-mini-tts", texto="oi", voz="marin", instrucoes="calmo"
        )
        assert obtida.conteudo == conteudo
