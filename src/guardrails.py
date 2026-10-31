"""Guardrails em camadas (RF16): entrada, conteúdo recuperado e saída, mais limites de recursos.

Cada camada devolve schemas.DecisaoGuardrail e vira um evento na auditoria, sem
reproduzir o texto bloqueado nem segredo.
"""

from __future__ import annotations

from .config import Config
from .schemas import DecisaoGuardrail, RespostaRAG, TrechoRecuperado
from .tipos import PendenteDeImplementacao


class LimiteExecucao(Exception):
    """Teto de chamadas ou de tokens da execução atingido (config["limites"])."""


def verificar_entrada(texto: str, *, config: Config) -> DecisaoGuardrail:
    """RF16 — parte: guardrails.

    Esperado: comprimento (limites.max_caracteres_solicitacao), escopo do atendimento e moderação por regras
    documentadas ou serviço; tentativa de obter segredo ou de mudar regras vira "bloquear" ou "revisar".
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
    """RF16 — parte: guardrails.

    Esperado: conta chamadas e tokens de uma execução e levanta LimiteExecucao ao passar de
    limites.max_chamadas_por_execucao ou limites.max_tokens_por_execucao; no máximo
    limites.repeticoes_falha_transitoria nova tentativa para falha transitória (ServicoIndisponivel).
    """

    def __init__(self, config: Config):
        self.config = config

    def registrar(self, tokens: int | None) -> None:
        raise PendenteDeImplementacao("RF16", "guardrails")
