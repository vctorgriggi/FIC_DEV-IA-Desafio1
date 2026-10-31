"""Guardrails em camadas (RF16): entrada, conteúdo recuperado e saída, mais limites de recursos.

Cada camada devolve schemas.DecisaoGuardrail e vira um evento na auditoria, sem
reproduzir o texto bloqueado nem segredo.
"""

from __future__ import annotations

from .config import Config
from .llm_client import ErroLLM
from .schemas import DecisaoGuardrail, RespostaRAG, TrechoRecuperado
from .tipos import PendenteDeImplementacao


class LimiteExecucao(ErroLLM):
    mensagem_padrao = "Limite de chamadas ou de tokens desta execução atingido (limites no config.json)."


def verificar_entrada(texto: str, *, config: Config) -> DecisaoGuardrail:
    """RF16 — parte: guardrails.

    Esperado: comprimento (limites.max_caracteres_solicitacao), escopo do atendimento e moderação por regras
    documentadas ou serviço; tentativa de obter segredo ou de mudar regras vira "bloquear" ou "revisar".
    """
    raise PendenteDeImplementacao("RF16", "guardrails")


def verificar_arquivo(nome: str, tamanho_bytes: int, *, config: Config) -> DecisaoGuardrail:
    """RF16 — parte: guardrails.

    Esperado: extensão em acervo.extensoes e tamanho até acervo.tamanho_max_mb para documento incluído pela
    interface; arquivo excessivo é "bloquear" (T05), com o motivo sem o conteúdo do arquivo.
    """
    raise PendenteDeImplementacao("RF16", "guardrails")


def verificar_trechos(trechos: list[TrechoRecuperado], *, config: Config) -> list[DecisaoGuardrail]:
    """RF16 — parte: guardrails.

    Esperado: uma decisão por trecho recuperado; instrução embutida no acervo é dado não confiável e marca o
    trecho para revisão, sem nunca virar comando.
    """
    raise PendenteDeImplementacao("RF16", "guardrails")


def verificar_saida(resposta: RespostaRAG, *, config: Config) -> DecisaoGuardrail:
    """RF16 — parte: guardrails.

    Esperado: toda fonte citada está entre os trechos recuperados; sem dado pessoal indevido; status coerente
    (resposta "fundamentada" sem fonte é bloqueada); nada de autorizar envio.
    """
    raise PendenteDeImplementacao("RF16", "guardrails")


class ControleRecursos:
    """RF16 — parte: guardrails. Uma instância por execução, passada a ClienteLLM(controle=...).

    Esperado: antes_da_chamada levanta LimiteExecucao quando a próxima chamada passaria de
    limites.max_chamadas_por_execucao ou quando os tokens já passaram de limites.max_tokens_por_execucao;
    registrar soma os tokens (None quando o provedor não informa, como na voz). A repetição única em falha
    transitória já está no ClienteLLM e conta como chamada.
    """

    def __init__(self, config: Config):
        self.config = config

    def antes_da_chamada(self) -> None:
        raise PendenteDeImplementacao("RF16", "guardrails")

    def registrar(self, tokens: int | None) -> None:
        raise PendenteDeImplementacao("RF16", "guardrails")
