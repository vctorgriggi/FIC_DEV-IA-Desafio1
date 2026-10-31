"""Fluxo integrado do Desafio 2 (seção 9 do enunciado): solicitação até minuta fundamentada pendente.

Entrada e proteção -> Compreensão -> Recuperação e geração -> minuta "pendente" para revisão.
A interface chama só este módulo, as funções de leitura das partes e o revisao.py.
"""

from __future__ import annotations

from .audit import Auditoria
from .config import Config
from .embeddings import IndiceVetorial
from .llm_client import ClienteLLM
from .schemas import RegistroMinutaRAG
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
) -> RegistroMinutaRAG:
    """RF19/RF21 — parte: RAG.

    Esperado, nesta ordem, com um evento de auditoria por etapa (como fluxo._etapa do Desafio 1):
    1. guardrails.verificar_entrada; "bloquear" para aqui com status "bloqueada", guardando entrada e decisão;
    2. nlp.extrair_solicitacao e nlp.validar_regras; estrutura inválida ou incoerente para com status "bloqueada"
       e os problemas em problemas_validacao, antes de qualquer minuta (RF14);
    3. nlp.compreender (ficha do RF15);
    4. rag.minuta_fundamentada, guardrails.verificar_trechos e guardrails.verificar_saida;
    5. revisao.gravar_registro_rag com status "pendente" (resultados/minutas_rag/, não resultados/minutas,
       cuja taxa de aprovação é a do Desafio 1 em revisao.resumo_revisoes).
    O `cliente` chega com guardrails.ControleRecursos (ClienteLLM(controle=...)) e o limite vale para a execução.
    Auditoria (RF21): versão do esquema (schemas.ESQUEMA_VERSAO) e dos prompts (Resultado.prompt), perfil e
    modelo de geração, consulta, ids recuperados, índice (modelo de embedding e chunking), latência, tokens e
    custo (Resultado.respostas) e erros; identificadores mascarados (privacidade.mascarar).
    """
    raise PendenteDeImplementacao("RF19", "RAG")
