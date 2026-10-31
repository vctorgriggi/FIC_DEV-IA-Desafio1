"""Exemplos válidos dos contratos do Desafio 2, para testar uma parte sem esperar as outras.

Ex.: o Estudante 3 testa revisao.registrar_decisao_rag gravando registro("pendente") com
revisao.gravar_registro_rag, sem precisar do fluxo do Estudante 2.
"""

from src.schemas import (
    ESQUEMA_VERSAO,
    Afirmacao,
    AvaliacaoSentimento,
    DecisaoGuardrail,
    Entidades,
    FichaCompreensao,
    RegistroMinutaRAG,
    RespostaRAG,
    SolicitacaoEstruturada,
    Trecho,
    TrechoRecuperado,
)


def entidades(**campos) -> Entidades:
    return Entidades(**{"pessoas": [], "orgaos": [], "locais": [], "datas": [], "protocolos": [], **campos})


def solicitacao(**campos) -> SolicitacaoEstruturada:
    base = {
        "protocolo": "2026-000001", "data": "01/10/2026", "solicitante": "Pessoa Fictícia", "assunto": "Matrícula",
        "pedido": "Informar documentos", "categoria": "matricula",
        "entidades": entidades(pessoas=["Pessoa Fictícia"], protocolos=["2026-000001"]),
        "campos_ausentes": [], "necessita_revisao": False, "motivo_revisao": "",
    }
    return SolicitacaoEstruturada(**{**base, **campos})


def ficha(**campos) -> FichaCompreensao:
    return FichaCompreensao(**{"resumo": "Pede a lista de documentos da matrícula.", "inferencias": [], **campos})


def trecho(**campos) -> Trecho:
    base = {"id": "DOC-01:abc123:A:0", "documento_id": "DOC-01", "titulo": "Guia fictício", "versao": "1.0",
            "hash_documento": "abc123", "chunking": "A", "texto": "Documentos exigidos: RG e histórico."}
    return Trecho(**{**base, **campos})


def resposta_rag(**campos) -> RespostaRAG:
    recuperado = TrechoRecuperado(trecho=trecho(), distancia=0.2)
    base = {"status": "fundamentada", "resposta": "Apresente RG e histórico.",
            "afirmacoes": [Afirmacao(texto="Apresente RG e histórico.", fontes=[recuperado.trecho.id])],
            "trechos": [recuperado], "necessita_revisao": False}
    return RespostaRAG(**{**base, **campos})


def registro(status: str = "pendente", **campos) -> RegistroMinutaRAG:
    bloqueada = status == "bloqueada"
    base = {
        "id_execucao": "abc123def456", "status": status, "criado_em": "2026-10-31T12:00:00-04:00",
        "origem": "teste", "esquema_versao": ESQUEMA_VERSAO, "perfil_geracao": "principal",
        "entrada": "Solicitação fictícia.",
        "guardrails": [DecisaoGuardrail(decisao="bloquear" if bloqueada else "permitir", camada="entrada",
                                        regra="exemplo", motivo="exemplo")],
        "problemas_validacao": [],
        "solicitacao": None if bloqueada else solicitacao(),
        "ficha": None if bloqueada else ficha(),
        "resposta": None if bloqueada else resposta_rag(),
        "decisao": None,
    }
    return RegistroMinutaRAG(**{**base, **campos})


def avaliacao(**campos) -> AvaliacaoSentimento:
    base = {"id": "AV-01", "polaridade": "positiva", "justificativa": "Elogia o atendimento.",
            "necessita_revisao": False, "confianca_declarada": None}
    return AvaliacaoSentimento(**{**base, **campos})
