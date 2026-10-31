"""Contratos de dados do Desafio 2 (RF14, RF15, RF16, RF17, RF19, RF22).

As partes de cada estudante trocam estes tipos. Campo novo, renomeado ou
removido é versão nova de ESQUEMA_VERSAO, combinada com o grupo e feita no
mesmo commit que ajusta quem produz e quem consome o tipo.

Os modelos que o modelo de linguagem preenche viram esquema de saída com
llm_client.formato_json(Modelo.model_json_schema(), nome).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ESQUEMA_VERSAO = "2.0"
LIMITE_PALAVRAS_RESUMO = 100

DecisaoGuardrailTipo = Literal["permitir", "bloquear", "revisar"]
StatusResposta = Literal["fundamentada", "sem_evidencia", "conflito"]
# Seção 4 do enunciado: pendente, aprovada, rejeitada e revisar precisam ser preservados.
# "bloqueada" é a solicitação parada antes da minuta (RF14, RF16): não há minuta para decidir.
StatusMinuta = Literal["pendente", "aprovada", "rejeitada", "revisar", "bloqueada"]
DecisaoOperadorTipo = Literal["aprovar", "rejeitar", "revisar"]
Polaridade = Literal["positiva", "negativa", "neutra", "indeterminada"]


class _Estrito(BaseModel):
    # extra="forbid": chave extra é erro. strict=True: "true", 1 ou "2026" não viram bool ou str por coerção.
    # Os dois juntos separam chave extra, tipo incorreto e campo ausente (RF14).
    model_config = ConfigDict(extra="forbid", strict=True)


# --- RF14 e RF15: solicitação ------------------------------------------------


class Entidades(_Estrito):
    """Entidades presentes no texto, copiadas literalmente; nada completado por suposição."""

    pessoas: list[str]
    orgaos: list[str]
    locais: list[str]
    datas: list[str]
    protocolos: list[str]


class SolicitacaoEstruturada(_Estrito):
    """Contrato de dados da solicitação (RF14) e fonte única de categoria e entidades.

    Ausência é null e entra em campos_ausentes; a interface mostra null como "não localizado".
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
    """O que o RF15 acrescenta à solicitação: resumo e inferências. Categoria e entidades vêm da SolicitacaoEstruturada."""

    resumo: str
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
    camada: Literal["entrada", "arquivo", "trechos", "saida", "recursos"]
    regra: str
    motivo: str


# --- RF17 e RF19: acervo, índice e RAG ------------------------------------------


class DocumentoAcervo(BaseModel):
    """Entrada do manifesto do acervo (dados/acervo/acervo.json). Sem strict: a data vem como texto do JSON."""

    model_config = ConfigDict(extra="forbid")

    id: str
    titulo: str
    versao: str
    arquivo: str
    tema: str
    vigencia_inicio: date | None = None
    # Ids dos documentos que este altera; com vigência, resolve conflito de fontes (seção 6).
    substitui: list[str] = Field(default_factory=list)


class Trecho(_Estrito):
    """Unidade indexada (chunk) com o que a citação precisa para ser conferida (RF17, RF19).

    pagina e secao têm default porque o Chroma descarta metadado None ao gravar.
    """

    id: str
    documento_id: str
    titulo: str
    versao: str
    hash_documento: str
    chunking: str
    texto: str
    pagina: int | None = None
    secao: str | None = None


class TrechoRecuperado(_Estrito):
    trecho: Trecho
    # Distância de cosseno do Chroma: 0 é idêntico, 2 é oposto. Proximidade não garante que o trecho responde.
    distancia: float


class Afirmacao(_Estrito):
    """Uma afirmação da resposta e os ids dos trechos que a sustentam (RF19: conferir cada afirmação)."""

    texto: str
    fontes: list[str]


class RespostaGerada(_Estrito):
    """O que o modelo de linguagem devolve no RAG; esquema de saída da geração."""

    status: StatusResposta
    resposta: str
    afirmacoes: list[Afirmacao]


class RespostaRAG(RespostaGerada):
    """RespostaGerada com os trechos que foram ao modelo (RF19). Fonte citada fora de `trechos` é erro de saída (RF16)."""

    trechos: list[TrechoRecuperado]
    necessita_revisao: bool

    def fontes(self) -> list[str]:
        """Ids de todos os trechos citados. Método, não campo: o registro gravado relê sem chave extra."""
        return sorted({fonte for afirmacao in self.afirmacoes for fonte in afirmacao.fontes})


# --- Registro da minuta (RF19, RF20, RF21, RF24) ---------------------------------


class DecisaoOperador(_Estrito):
    decisao: DecisaoOperadorTipo
    justificativa: str
    revisor: str
    data_hora: str


class RegistroMinutaRAG(_Estrito):
    """O que fluxo_rag grava em resultados/minutas_rag/<id>.json e revisao.registrar_decisao_rag atualiza.

    status "bloqueada" tem solicitacao, ficha e resposta possivelmente None, e guardrails ou
    problemas_validacao dizem por quê; só "pendente" aceita decisão do operador.
    """

    id_execucao: str
    status: StatusMinuta
    criado_em: str
    origem: str
    esquema_versao: str
    perfil_geracao: str
    entrada: str
    guardrails: list[DecisaoGuardrail]
    problemas_validacao: list[str]
    solicitacao: SolicitacaoEstruturada | None
    ficha: FichaCompreensao | None
    resposta: RespostaRAG | None
    decisao: DecisaoOperador | None


# --- RF22: sentimentos ------------------------------------------------------------


class AvaliacaoSentimento(_Estrito):
    """Classificação de uma avaliação de atendimento. Não descreve a pessoa que escreveu."""

    id: str
    polaridade: Polaridade
    justificativa: str
    necessita_revisao: bool
    # Estimativa declarada pelo modelo, não calibrada: não é probabilidade de acerto nem entra em contagem.
    confianca_declarada: float | None
