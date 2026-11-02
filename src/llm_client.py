"""Cliente único do provedor de modelos (RF04).

Todas as chamadas à OpenAI passam por aqui: modelo, parâmetros, timeout e
armazenamento no provedor vêm do config.json; a chave vem do .env.
"""

from __future__ import annotations

import base64
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .config import Config, carregar_chave
from .privacidade import ocultar_segredos


class ErroLLM(Exception):
    """Falha do provedor com mensagem para o operador; nunca carrega a chave."""

    mensagem_padrao = "Falha ao chamar o modelo."

    def __init__(self, mensagem: str | None = None, *, status: int | None = None, detalhe: str = ""):
        super().__init__(mensagem or self.mensagem_padrao)
        self.status = status
        self.detalhe = detalhe


class ChaveAusente(ErroLLM):
    mensagem_padrao = "Chave da API não configurada. Copie .env.example para .env e preencha OPENAI_API_KEY."


class AutenticacaoInvalida(ErroLLM):
    mensagem_padrao = "O provedor recusou a chave da API. Confira OPENAI_API_KEY no .env."


class LimiteRequisicoes(ErroLLM):
    mensagem_padrao = "Limite de requisições ou cota do provedor atingido. Aguarde alguns minutos e tente de novo."


class ServicoIndisponivel(ErroLLM):
    mensagem_padrao = "O serviço do modelo está indisponível no momento. Tente novamente mais tarde."


class TempoEsgotado(ServicoIndisponivel):
    mensagem_padrao = "O modelo não respondeu dentro do limite de tempo (timeout_segundos no config.json)."


class RequisicaoInvalida(ErroLLM):
    mensagem_padrao = "O provedor recusou a requisição. Confira o nome do modelo e os parâmetros no config.json."


class RespostaVazia(ErroLLM):
    mensagem_padrao = "O modelo devolveu uma resposta vazia."


class RespostaIncompleta(ErroLLM):
    mensagem_padrao = "A resposta do modelo foi cortada pelo limite de tokens (max_output_tokens no config.json)."


class RespostaMalformada(ErroLLM):
    mensagem_padrao = "O modelo devolveu uma resposta fora do formato pedido."


@dataclass
class RespostaLLM:
    texto: str
    modelo: str
    duracao_s: float
    tokens_entrada: int | None
    tokens_saida: int | None
    custo_estimado_usd: float | None
    parametros: dict = field(default_factory=dict)
    # Áudio da síntese de voz e imagem gerada chegam aqui, já em bytes.
    conteudo: bytes | None = field(repr=False, default=None)
    # Objeto devolvido pelo SDK, para metadados que só uma tarefa usa (ex.: idiomas da transcrição).
    bruta: Any = field(repr=False, default=None)


@dataclass
class RespostaEmbeddings:
    vetores: list[list[float]]
    modelo: str
    dimensao: int
    duracao_s: float
    tokens_entrada: int | None
    custo_estimado_usd: float | None


class ClienteLLM:
    def __init__(self, config: Config, *, chave: str | None = None, sdk: Any = None, controle: Any = None):
        """`controle` (guardrails.ControleRecursos, RF16) é avisado antes de cada chamada e recebe os tokens depois."""
        self.config = config
        self.controle = controle
        self._chave = chave or carregar_chave()
        if sdk is None:
            if not self._chave:
                raise ChaveAusente()
            from openai import OpenAI

            # O SDK repete 408, 409, 429 e 5xx duas vezes por padrão; num 429 de cota
            # esgotada isso só atrasa a mesma recusa. Sem repetição, o 429 volta na
            # hora como LimiteRequisicoes, e o prazo de relógio em _chamar cobre o resto.
            sdk = OpenAI(api_key=self._chave, max_retries=0)
        self._sdk = sdk

    def nova_execucao(self, controle: Any) -> ClienteLLM:
        """Reutiliza o adaptador com orçamento independente, sem recriar conexão."""
        return ClienteLLM(self.config, chave=self._chave, sdk=self._sdk, controle=controle)

    def gerar(
        self,
        *,
        modelo: str,
        entrada: str | list[dict],
        instrucao_sistema: str | None = None,
        formato_resposta: dict | None = None,
        parametros: dict | None = None,
    ) -> RespostaLLM:
        """Gera texto pela Responses API e devolve texto, tempo, tokens e custo estimado.

        `entrada` é texto puro ou a lista de mensagens da Responses API (ver
        entrada_com_anexo). `formato_resposta` vem de formato_json.
        """
        parametros = {
            "store": self.config.dados["armazenar_no_provedor"],
            **self.config.dados.get("parametros_geracao", {}),
            **(parametros or {}),
        }
        argumentos: dict[str, Any] = {"model": modelo, "input": entrada, **parametros}
        if instrucao_sistema:
            argumentos["instructions"] = instrucao_sistema
        if formato_resposta:
            argumentos["text"] = formato_resposta
            parametros["formato_resposta"] = formato_resposta["format"]["name"]

        resposta, duracao = self._executar(lambda: self._sdk.responses.create(**argumentos, timeout=self._timeout()))

        uso = getattr(resposta, "usage", None)
        entrada_tokens, saida_tokens = getattr(uso, "input_tokens", None), getattr(uso, "output_tokens", None)
        self._contabilizar(entrada_tokens, saida_tokens)
        status = getattr(resposta, "status", "completed")
        if status == "incomplete":
            motivo = getattr(getattr(resposta, "incomplete_details", None), "reason", None)
            # O raciocínio conta no max_output_tokens; quando ele estoura, o JSON chega cortado.
            if motivo == "max_output_tokens":
                raise RespostaIncompleta()
            raise RespostaIncompleta(f"A resposta do modelo veio incompleta (motivo: {motivo or 'não informado'}).")
        if status == "failed":
            raise ServicoIndisponivel(detalhe=self._ocultar(str(getattr(resposta, "error", ""))))
        texto = (getattr(resposta, "output_text", None) or "").strip()
        if not texto:
            raise RespostaVazia()
        preco = self._preco(modelo)
        return RespostaLLM(
            texto=texto,
            modelo=modelo,
            duracao_s=duracao,
            tokens_entrada=entrada_tokens,
            tokens_saida=saida_tokens,
            # output_tokens já inclui o raciocínio, que é cobrado como saída.
            custo_estimado_usd=_custo([(entrada_tokens, preco.get("entrada")), (saida_tokens, preco.get("saida"))]),
            parametros=parametros,
            bruta=resposta,
        )

    def transcrever(
        self, *, modelo: str, nome_arquivo: str, conteudo: bytes, mime_type: str, idiomas: list[str] | None = None
    ) -> RespostaLLM:
        """Speech-to-text (RF06): devolve o texto; os idiomas detectados ficam em `bruta.languages`."""
        parametros: dict[str, Any] = {"languages": idiomas} if idiomas else {}
        resposta, duracao = self._executar(
            lambda: self._sdk.audio.transcriptions.create(
                model=modelo, file=(nome_arquivo, conteudo, mime_type), **parametros, timeout=self._timeout()
            )
        )
        texto = (getattr(resposta, "text", None) or "").strip()
        if not texto:
            raise RespostaVazia("Nenhuma fala transcrita. Confira se o áudio contém fala inteligível.")
        uso = getattr(resposta, "usage", None)
        tokens = getattr(uso, "type", None) == "tokens"
        self._contabilizar(getattr(uso, "total_tokens", None) if tokens else None)
        segundos = getattr(uso, "seconds", None) if getattr(uso, "type", None) == "duration" else None
        por_minuto = self.config.dados.get("precos_usd_por_minuto_audio", {}).get(modelo)
        return RespostaLLM(
            texto=texto,
            modelo=modelo,
            duracao_s=duracao,
            tokens_entrada=getattr(uso, "input_tokens", None) if tokens else None,
            tokens_saida=getattr(uso, "output_tokens", None) if tokens else None,
            custo_estimado_usd=round(segundos / 60 * por_minuto, 6) if segundos is not None and por_minuto else None,
            parametros=parametros,
            bruta=resposta,
        )

    def sintetizar_voz(self, *, modelo: str, texto: str, voz: str, instrucoes: str) -> RespostaLLM:
        """Text-to-speech (RF07): devolve o WAV em `conteudo`.

        A Speech API não informa tokens; o custo fica sem estimativa.
        """
        parametros = {"voice": voz, "instructions": instrucoes, "response_format": "wav"}
        resposta, duracao = self._executar(
            lambda: self._sdk.audio.speech.create(model=modelo, input=texto, **parametros, timeout=self._timeout())
        )
        conteudo = getattr(resposta, "content", None)
        if not conteudo:
            raise RespostaVazia("O provedor não retornou áudio.")
        conteudo = _wav_com_tamanhos(conteudo)
        self._contabilizar()
        return RespostaLLM(
            texto="",
            modelo=modelo,
            duracao_s=duracao,
            tokens_entrada=None,
            tokens_saida=None,
            custo_estimado_usd=None,
            parametros=parametros,
            conteudo=conteudo,
            bruta=resposta,
        )

    def gerar_imagem(
        self, *, modelo: str, prompt: str, tamanho: str, imagem_base: tuple[str, bytes, str] | None = None
    ) -> RespostaLLM:
        """Gera uma imagem PNG, ou edita `imagem_base` (nome, bytes, mime), e a devolve em `conteudo`."""
        parametros = {"size": tamanho, "output_format": "png", "n": 1}
        if imagem_base is None:
            chamada, extra = self._sdk.images.generate, {}
        else:
            chamada, extra = self._sdk.images.edit, {"image": imagem_base}
        resposta, duracao = self._executar(
            lambda: chamada(model=modelo, prompt=prompt, **extra, **parametros, timeout=self._timeout())
        )
        imagens = getattr(resposta, "data", None) or []
        dados = getattr(imagens[0], "b64_json", None) if imagens else None
        if not dados:
            raise RespostaVazia("O provedor não retornou imagem.")
        uso = getattr(resposta, "usage", None)
        detalhes = getattr(uso, "input_tokens_details", None)
        self._contabilizar(getattr(uso, "input_tokens", None), getattr(uso, "output_tokens", None))
        preco = self._preco(modelo)
        return RespostaLLM(
            texto="",
            modelo=modelo,
            duracao_s=duracao,
            tokens_entrada=getattr(uso, "input_tokens", None),
            tokens_saida=getattr(uso, "output_tokens", None),
            custo_estimado_usd=_custo(
                [
                    (getattr(detalhes, "text_tokens", None), preco.get("entrada")),
                    (getattr(detalhes, "image_tokens", None), preco.get("entrada_imagem")),
                    (getattr(uso, "output_tokens", None), preco.get("saida")),
                ]
            ),
            parametros=parametros,
            conteudo=base64.b64decode(dados),
            bruta=resposta,
        )

    def gerar_embeddings(self, *, modelo: str, textos: list[str]) -> RespostaEmbeddings:
        """Embeddings de uma lista de textos (RF17), na mesma ordem da entrada."""
        if not textos:
            raise ValueError("Nenhum texto para gerar embeddings.")
        resposta, duracao = self._executar(
            lambda: self._sdk.embeddings.create(model=modelo, input=textos, timeout=self._timeout())
        )
        dados = sorted(getattr(resposta, "data", None) or [], key=lambda item: item.index)
        if len(dados) != len(textos):
            raise RespostaMalformada(f"O provedor devolveu {len(dados)} embeddings para {len(textos)} textos.")
        vetores = [list(item.embedding) for item in dados]
        tokens = getattr(getattr(resposta, "usage", None), "prompt_tokens", None)
        self._contabilizar(tokens)
        return RespostaEmbeddings(
            vetores=vetores,
            modelo=modelo,
            dimensao=len(vetores[0]),
            duracao_s=duracao,
            tokens_entrada=tokens,
            custo_estimado_usd=_custo([(tokens, self._preco(modelo).get("entrada"))]),
        )

    def _timeout(self) -> float:
        return self.config.dados["timeout_segundos"]

    def _preco(self, modelo: str) -> dict:
        return self.config.dados.get("precos_usd_por_milhao_tokens", {}).get(modelo) or {}

    def _ocultar(self, texto: str) -> str:
        return ocultar_segredos(texto, [self._chave or ""])[:500]

    def _executar(self, operacao: Callable[[], Any]) -> tuple[Any, float]:
        # RF16: no máximo limites.repeticoes_falha_transitoria novas tentativas, só para 5xx e conexão.
        # 429 e timeout não se repetem: o primeiro só atrasaria a mesma recusa, o segundo dobraria a espera.
        repeticoes = self.config.dados.get("limites", {}).get("repeticoes_falha_transitoria", 0)
        tentativas = 1 + max(0, min(1, repeticoes))
        for tentativa in range(tentativas):
            if self.controle is not None:
                self.controle.antes_da_chamada()
            inicio = time.perf_counter()
            try:
                resultado = self._chamar(operacao)
            except Exception as erro:
                convertido = self._converter_erro(erro)
                if convertido is None:
                    raise
                transitoria = isinstance(convertido, ServicoIndisponivel) and not isinstance(convertido, TempoEsgotado)
                if transitoria and tentativa + 1 < tentativas:
                    continue
                # from None: o encadeamento levaria a requisição original para o traceback.
                raise convertido from None
            return resultado, round(time.perf_counter() - inicio, 3)
        raise AssertionError("inalcançável: a última tentativa devolve ou levanta")

    def _contabilizar(self, *tokens: int | None) -> None:
        if self.controle is not None:
            self.controle.registrar(sum(t for t in tokens if t) or None)

    def _chamar(self, operacao: Callable[[], Any]) -> Any:
        """Chama o SDK com prazo de relógio de timeout_segundos, seja qual for o motivo da demora."""
        resultado: dict[str, Any] = {}

        def alvo() -> None:
            try:
                resultado["resposta"] = operacao()
            except BaseException as erro:  # devolvido à thread principal logo abaixo
                resultado["erro"] = erro

        # daemon: se o SDK seguir preso, a thread não impede o processo de terminar.
        linha = threading.Thread(target=alvo, daemon=True)
        linha.start()
        linha.join(self._timeout())
        if linha.is_alive():
            raise TempoEsgotado()
        if "erro" in resultado:
            raise resultado["erro"]
        return resultado["resposta"]

    def _converter_erro(self, erro: Exception) -> ErroLLM | None:
        # Classificar por atributo (status_code, nome da classe) mantém os testes sem rede;
        # testes/test_llm_client.py usa as classes reais do SDK.
        nome = type(erro).__name__
        status = getattr(erro, "status_code", None)
        detalhe = self._ocultar(str(erro))

        if "Timeout" in nome:
            return TempoEsgotado(detalhe=detalhe)
        if "Connection" in nome:
            return ServicoIndisponivel(detalhe=detalhe)
        if status is None:
            return None
        if status in (401, 403):
            return AutenticacaoInvalida(status=status, detalhe=detalhe)
        if status == 429:
            return LimiteRequisicoes(status=status, detalhe=detalhe)
        if status >= 500:
            return ServicoIndisponivel(status=status, detalhe=detalhe)
        return RequisicaoInvalida(status=status, detalhe=detalhe)


def ler_json(resposta: RespostaLLM) -> dict:
    """JSON de uma resposta pedida com formato_json; fora do formato, RespostaMalformada."""
    try:
        dados = json.loads(resposta.texto)
    except json.JSONDecodeError:
        raise RespostaMalformada() from None
    if not isinstance(dados, dict):
        raise RespostaMalformada()
    return dados


def formato_json(esquema: dict, nome: str) -> dict:
    """Parâmetro `text` para saída JSON validada por esquema (Structured Outputs, modo estrito).

    O modo estrito exige additionalProperties false em todo objeto; o esquema
    das partes fica sem isso e é ajustado aqui.
    """
    return {"format": {"type": "json_schema", "name": nome, "schema": _estrito(esquema), "strict": True}}


def entrada_com_anexo(texto: str, *, nome_arquivo: str, mime_type: str, conteudo: bytes) -> list[dict]:
    """Mensagem com instrução e um anexo inline: PDF como input_file, imagem como input_image."""
    url = f"data:{mime_type};base64,{base64.b64encode(conteudo).decode('ascii')}"
    if mime_type == "application/pdf":
        anexo = {"type": "input_file", "filename": nome_arquivo, "file_data": url}
    else:
        anexo = {"type": "input_image", "image_url": url}
    return [{"role": "user", "content": [{"type": "input_text", "text": texto}, anexo]}]


def _estrito(esquema: Any) -> Any:
    """Todo objeto fechado e com todas as propriedades obrigatórias, como o modo estrito pede.

    Valor padrão do Pydantic sai do esquema: o modelo preenche sempre todos os campos,
    e ausência é null, não omissão.
    """
    if isinstance(esquema, list):
        return [_estrito(item) for item in esquema]
    if not isinstance(esquema, dict):
        return esquema
    ajustado: dict = {}
    for chave, valor in esquema.items():
        if chave == "default":
            continue
        if chave in ("properties", "$defs"):
            ajustado[chave] = {nome: _estrito(sub) for nome, sub in valor.items()}
        else:
            ajustado[chave] = _estrito(valor)
    if ajustado.get("type") == "object":
        ajustado["additionalProperties"] = False
        ajustado["required"] = list(ajustado.get("properties", {}))
    return ajustado


_TAMANHO_DESCONHECIDO = 0xFFFFFFFF


def _wav_com_tamanhos(conteudo: bytes) -> bytes:
    """Preenche os tamanhos de um WAV gerado em streaming; qualquer outro WAV volta intacto.

    A Speech API devolve o RIFF e o bloco data com tamanho 0xFFFFFFFF, como em
    streaming; sem o tamanho real, o arquivo não passa em audio.validar_wav.
    """
    if conteudo[:4] != b"RIFF" or conteudo[8:12] != b"WAVE" or int.from_bytes(conteudo[4:8], "little") != _TAMANHO_DESCONHECIDO:
        return conteudo
    posicao = 12
    while posicao + 8 <= len(conteudo):
        bloco, tamanho = conteudo[posicao:posicao + 4], int.from_bytes(conteudo[posicao + 4:posicao + 8], "little")
        if bloco == b"data":
            if tamanho != _TAMANHO_DESCONHECIDO:
                return conteudo
            dados = len(conteudo) - (posicao + 8)
            return b"".join(
                [
                    b"RIFF",
                    (len(conteudo) - 8).to_bytes(4, "little"),
                    conteudo[8:posicao + 4],
                    dados.to_bytes(4, "little"),
                    conteudo[posicao + 8:],
                ]
            )
        posicao += 8 + tamanho + tamanho % 2
    return conteudo


def _custo(partes: list[tuple[int | None, float | None]]) -> float | None:
    """Soma tokens × preço por milhão; sem algum dos números, não há estimativa."""
    if not partes or any(tokens is None or preco is None for tokens, preco in partes):
        return None
    return round(sum(tokens * preco for tokens, preco in partes) / 1_000_000, 6)
