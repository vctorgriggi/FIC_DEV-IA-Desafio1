"""Contratos de dados do Desafio 2 (RF14, RF15, RF16, RF17, RF19, RF22).

As partes de cada estudante trocam estes tipos. Campo novo, renomeado ou
removido é versão nova de ESQUEMA_VERSAO, combinada com o grupo e feita no
mesmo commit que ajusta quem produz e quem consome o tipo.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ESQUEMA_VERSAO = "2.0"
LIMITE_PALAVRAS_RESUMO = 100

DecisaoGuardrailTipo = Literal["permitir", "bloquear", "revisar"]
StatusResposta = Literal["fundamentada", "sem_evidencia", "conflito"]
# Seção 4 do enunciado: estes quatro estados precisam ser preservados.
StatusMinuta = Literal["pendente", "aprovada", "rejeitada", "revisar"]
Polaridade = Literal["positiva", "negativa", "neutra", "indeterminada"]


class _Estrito(BaseModel):
    # Chave extra é erro de esquema (RF14: diferenciar chaves extras, tipo incorreto e campo ausente).
    model_config = ConfigDict(extra="forbid")


# --- RF14 e RF15: solicitação ------------------------------------------------


class Entidades(_Estrito):
    """Entidades presentes no texto, copiadas literalmente; nada completado por suposição."""

    pessoas: list[str] = Field(default_factory=list)
    orgaos: list[str] = Field(default_factory=list)
    locais: list[str] = Field(default_factory=list)
    datas: list[str] = Field(default_factory=list)
    protocolos: list[str] = Field(default_factory=list)


class SolicitacaoEstruturada(_Estrito):
    """Contrato de dados da solicitação (RF14). Ausência é null e entra em campos_ausentes.

    A interface mostra null como "não localizado"; o JSON guarda null.
    """

    protocolo: str | None
    data: str | None
    solicitante: str | None
    assunto: str | None
    pedido: str | None
    categoria: str | None
    entidades: Entidades
    campos_ausentes: list[str]
    necessita_revisao: bool
    motivo_revisao: str


class Inferencia(_Estrito):
    """Informação que não está escrita na solicitação, separada da extração literal (RF15)."""

    campo: str
    valor: str
    justificativa: str


class FichaCompreensao(_Estrito):
    """Ficha de compreensão da solicitação (RF15)."""

    resumo: str
    categoria: str
    entidades: Entidades
    inferencias: list[Inferencia]

    @field_validator("resumo")
    @classmethod
    def _resumo_curto(cls, resumo: str) -> str:
        if len(resumo.split()) > LIMITE_PALAVRAS_RESUMO:
            raise ValueError(f"O resumo passa de {LIMITE_PALAVRAS_RESUMO} palavras.")
        return resumo


# --- RF16: guardrails ---------------------------------------------------------


class DecisaoGuardrail(_Estrito):
    """Resultado de uma camada de guardrail. O motivo nunca reproduz segredo nem o texto bloqueado."""

    decisao: DecisaoGuardrailTipo
    regra: str
    motivo: str


# --- RF17 e RF19: acervo, índice e RAG ------------------------------------------


class DocumentoAcervo(_Estrito):
    """Entrada do manifesto do acervo (dados/acervo/acervo.json)."""

    id: str
    titulo: str
    versao: str
    arquivo: str
    tema: str
    vigencia_inicio: date | None = None
    # Ids dos documentos que este altera; com vigência, resolve conflito de fontes (seção 6).
    substitui: list[str] = Field(default_factory=list)


class Trecho(_Estrito):
    """Unidade indexada (chunk) com o que a citação precisa para ser conferida (RF17, RF19)."""

    id: str
    documento_id: str
    titulo: str
    versao: str
    hash_documento: str
    pagina: int | None
    secao: str | None
    texto: str
    chunking: str


class TrechoRecuperado(_Estrito):
    trecho: Trecho
    # Distância de cosseno do Chroma: 0 é idêntico, 2 é oposto. Proximidade não garante que o trecho responde.
    distancia: float


class RespostaRAG(_Estrito):
    """Resposta fundamentada, abstenção ou conflito (RF19). fontes são ids de Trecho citados."""

    status: StatusResposta
    resposta: str
    fontes: list[str]
    trechos: list[TrechoRecuperado]
    necessita_revisao: bool


# --- RF22: sentimentos ------------------------------------------------------------


class AvaliacaoSentimento(_Estrito):
    """Classificação de uma avaliação de atendimento. Não descreve a pessoa que escreveu."""

    id: str
    polaridade: Polaridade
    justificativa: str
    necessita_revisao: bool
    # Estimativa declarada pelo modelo, não calibrada: não é probabilidade de acerto.
    confianca_declarada: float | None = None
