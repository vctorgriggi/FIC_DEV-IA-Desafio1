"""Fluxo integrado do Desafio 2 (seção 9 do enunciado): solicitação até minuta fundamentada pendente.

Entrada e proteção -> Compreensão -> Recuperação e geração -> minuta "pendente" para revisão.
A interface chama só este módulo e o revisao.py.
"""

from __future__ import annotations

from .audit import Auditoria
from .config import Config
from .embeddings import IndiceVetorial
from .llm_client import ClienteLLM
from .tipos import PendenteDeImplementacao


def processar_solicitacao(
    texto: str,
    *,
    origem: str,
    config: Config,
    cliente: ClienteLLM,
    indice: IndiceVetorial,
    auditoria: Auditoria,
    perfil: str | None = None,
) -> dict:
    """RF19/RF21 — parte: RAG.

    Esperado, nesta ordem, com um evento de auditoria por etapa (como fluxo._etapa do Desafio 1):
    1. guardrails.verificar_entrada; "bloquear" para aqui, guardando entrada, decisão e motivo;
    2. nlp.extrair_solicitacao e nlp.validar_regras; estrutura inválida ou incoerente bloqueia antes da minuta (RF14);
    3. nlp.compreender (ficha do RF15);
    4. rag.minuta_fundamentada, guardrails.verificar_trechos e guardrails.verificar_saida;
    5. gravar entrada, solicitação, ficha, resposta e trechos em config.caminho("minutas_rag")/<id>.json, com
       status "pendente"; não em resultados/minutas, cuja taxa de aprovação é a do Desafio 1 (revisao.resumo_revisoes).
    Auditoria (RF21): versão do esquema (schemas.ESQUEMA_VERSAO) e do prompt, perfil e modelo de geração,
    consulta, ids recuperados, índice (modelo de embedding e perfil de chunking), latência, tokens, custo e erros;
    identificadores mascarados (privacidade.mascarar). Devolve o registro gravado.
    """
    raise PendenteDeImplementacao("RF19", "RAG")
