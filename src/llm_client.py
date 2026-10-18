"""Cliente único do provedor de modelos (RF04).

Todas as chamadas ao Gemini passam por aqui: modelo, parâmetros, timeout e
armazenamento no provedor vêm do config.json; a chave vem do .env.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from .config import Config, carregar_chave
from .privacidade import ocultar_segredos


# Campo da Interaction onde cada tipo de saída chega.
CAMPOS_SAIDA = {"texto": "output_text", "audio": "output_audio", "imagem": "output_image"}


class ErroLLM(Exception):
    """Falha do provedor com mensagem para o operador; nunca carrega a chave."""

    mensagem_padrao = "Falha ao chamar o modelo."

    def __init__(self, mensagem: str | None = None, *, status: int | None = None, detalhe: str = ""):
        super().__init__(mensagem or self.mensagem_padrao)
        self.status = status
        self.detalhe = detalhe


class ChaveAusente(ErroLLM):
    mensagem_padrao = "Chave da API não configurada. Copie .env.example para .env e preencha GEMINI_API_KEY."


class AutenticacaoInvalida(ErroLLM):
    mensagem_padrao = "O provedor recusou a chave da API. Confira GEMINI_API_KEY no .env."


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
    # Interaction do SDK: áudio (output_audio) e imagem (output_image) saem daqui.
    bruta: Any = field(repr=False, default=None)


class ClienteLLM:
    def __init__(self, config: Config, *, chave: str | None = None, sdk: Any = None):
        self.config = config
        self._chave = chave or carregar_chave()
        if sdk is None:
            if not self._chave:
                raise ChaveAusente()
            from google import genai

            sdk = genai.Client(api_key=self._chave)
        self._sdk = sdk

    def gerar(
        self,
        *,
        modelo: str,
        entrada: str | list[dict],
        instrucao_sistema: str | None = None,
        formato_resposta: dict | None = None,
        parametros: dict | None = None,
        saida: str = "texto",
    ) -> RespostaLLM:
        """Faz uma chamada ao provedor e devolve texto, tempo, tokens e custo estimado.

        `entrada` é texto puro ou a lista de partes da Interactions API, por exemplo
        [{"type": "text", "text": ...}, {"type": "audio", "data": <base64>, "mime_type": "audio/mp3"}].
        `saida` diz o que precisa vir na resposta ("texto", "audio" ou "imagem");
        sem isso, levanta RespostaVazia. Áudio e imagem se leem em `bruta`.
        """
        if saida not in CAMPOS_SAIDA:
            raise ValueError(f"saida deve ser uma de {sorted(CAMPOS_SAIDA)}, não {saida!r}.")
        argumentos: dict[str, Any] = {
            "model": modelo,
            "input": entrada,
            "store": self.config.dados["armazenar_no_provedor"],
            "timeout": self.config.dados["timeout_segundos"],
        }
        parametros = {**self.config.dados.get("parametros_geracao", {}), **(parametros or {})}
        if parametros:
            argumentos["generation_config"] = parametros
        if instrucao_sistema:
            argumentos["system_instruction"] = instrucao_sistema
        if formato_resposta:
            argumentos["response_format"] = formato_resposta

        inicio = time.perf_counter()
        try:
            interacao = self._sdk.interactions.create(**argumentos)
        except Exception as erro:
            convertido = self._converter_erro(erro)
            if convertido is None:
                raise
            # from None: o encadeamento levaria a requisição original para o traceback.
            raise convertido from None
        duracao = time.perf_counter() - inicio

        texto = (getattr(interacao, "output_text", None) or "").strip()
        if not _tem_saida(interacao, saida):
            raise RespostaVazia()
        tokens_entrada, tokens_saida = _tokens(getattr(interacao, "usage", None))
        return RespostaLLM(
            texto=texto,
            modelo=modelo,
            duracao_s=round(duracao, 3),
            tokens_entrada=tokens_entrada,
            tokens_saida=tokens_saida,
            custo_estimado_usd=self._custo(modelo, tokens_entrada, tokens_saida, saida),
            parametros={k: v for k, v in argumentos.items() if k not in ("model", "input", "system_instruction")},
            bruta=interacao,
        )

    def _custo(self, modelo: str, entrada: int | None, saida: int | None, tipo_saida: str) -> float | None:
        preco = self.config.dados.get("precos_usd_por_milhao_tokens", {}).get(modelo)
        if not preco or entrada is None or saida is None:
            return None
        if tipo_saida == "imagem" and "por_imagem_1k" in preco:
            # Imagem gerada é cobrada por unidade; o config só tem o preço da resolução 1K.
            return round(entrada * preco["entrada"] / 1_000_000 + preco["por_imagem_1k"], 6)
        return round((entrada * preco["entrada"] + saida * preco["saida"]) / 1_000_000, 6)

    def _converter_erro(self, erro: Exception) -> ErroLLM | None:
        # As classes de erro da Interactions API ficam num módulo privado do SDK
        # (google.genai._gaos.lib.compat_errors); classificar por atributo evita
        # depender desse caminho. testes/test_llm_client.py usa as classes reais.
        nome = type(erro).__name__
        status = getattr(erro, "status_code", None)
        corpo = str(getattr(erro, "body", "") or "")
        detalhe = ocultar_segredos(str(erro), [self._chave or ""])[:500]

        if "Timeout" in nome:
            return TempoEsgotado(detalhe=detalhe)
        if "Connection" in nome:
            return ServicoIndisponivel(detalhe=detalhe)
        if status is None:
            return None
        # Chave inválida chega como 400 INVALID_ARGUMENT com reason API_KEY_INVALID.
        if status in (401, 403) or "API_KEY_INVALID" in corpo:
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


def formato_json(esquema: dict) -> dict:
    """response_format para saída JSON validada por esquema (docs Gemini API, structured output)."""
    return {"type": "text", "mime_type": "application/json", "schema": esquema}


def _tem_saida(interacao: Any, saida: str) -> bool:
    if saida == "texto":
        return bool((getattr(interacao, "output_text", None) or "").strip())
    conteudo = getattr(interacao, CAMPOS_SAIDA[saida], None)
    return bool(getattr(conteudo, "data", None) or getattr(conteudo, "uri", None))


def _tokens(uso: Any) -> tuple[int | None, int | None]:
    if uso is None:
        return None, None
    entrada = getattr(uso, "total_input_tokens", None)
    saida = getattr(uso, "total_output_tokens", None)
    # A tabela de preços cobra o raciocínio como saída; não confirmamos se
    # total_output_tokens já o inclui, então somamos explicitamente.
    pensamento = getattr(uso, "total_thought_tokens", None) or 0
    if saida is not None:
        saida += pensamento
    return entrada, saida
