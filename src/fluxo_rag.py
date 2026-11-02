"""Fluxo integrado do Desafio 2 (seção 9 do enunciado): solicitação até minuta fundamentada pendente.

Entrada e proteção -> Compreensão -> Recuperação e geração -> minuta "pendente" para revisão.
A interface chama só este módulo, as funções de leitura das partes e o revisao.py.
"""

from __future__ import annotations

import json

from . import guardrails, nlp, rag
from .audit import Auditoria, Evento, agora_iso, novo_id
from .config import Config
from .embeddings import IndiceVetorial
from .fluxo import _etapa
from .llm_client import ClienteLLM, RespostaLLM, RespostaMalformada
from .prompts import Prompt
from .revisao import caminho_registro_rag, gravar_registro_rag
from .schemas import ESQUEMA_VERSAO, DecisaoGuardrail, RegistroMinutaRAG


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
    """Guardrail de entrada, extração (RF14), ficha (RF15), minuta com fontes (RF19) e registro "pendente".

    Estrutura inválida, ficha inválida, resposta sem fundamento conferível ou guardrail "bloquear" param o fluxo
    com status "bloqueada", guardando entrada, problemas e decisões. Falha do provedor é auditada e levantada.
    O `cliente` chega com guardrails.ControleRecursos e o limite vale para a execução.
    """
    geracao = config.perfil_geracao(perfil)
    if cliente.controle is None:
        cliente = cliente.nova_execucao(guardrails.ControleRecursos(config))
    indice = indice.com_cliente(cliente)
    id_execucao = novo_id()
    base = {"id_execucao": id_execucao, "caso_id": rag.minimizar(origem, config), "modalidade": "solicitacao_d2"}
    comum = {"esquema_versao": ESQUEMA_VERSAO, "perfil_geracao": geracao["nome"], "modelo_geracao": geracao["modelo"]}
    registro = {
        "id_execucao": id_execucao, "status": "pendente", "criado_em": agora_iso(), "origem": origem,
        "esquema_versao": ESQUEMA_VERSAO, "perfil_geracao": geracao["nome"],
        # O registro guarda a entrada minimizada, a mesma que o provedor recebeu.
        "entrada": rag.minimizar(texto, config),
        "guardrails": [], "problemas_validacao": [], "solicitacao": None, "ficha": None, "resposta": None, "decisao": None,
    }

    with _etapa(auditoria, base, "d2_entrada") as evento:
        decisao = guardrails.verificar_entrada(texto, config=config)
        registro["guardrails"].append(decisao)
        evento.extra = {**comum, "guardrails": _decisoes([decisao])}
    if decisao.decisao == "bloquear":
        return _encerrar(config, auditoria, base, registro, "bloqueada")

    with _etapa(auditoria, base, "d2_extracao") as evento:
        try:
            extraida = nlp.extrair_solicitacao(texto, origem=origem, cliente=cliente, config=config, perfil=perfil)
            _anotar(evento, extraida.respostas, extraida.prompt)
            problemas = nlp.validar_regras(extraida.valor, rag.minimizar(texto, config), config=config)
        except RespostaMalformada as erro:
            _anotar(evento, getattr(erro, "respostas", []), getattr(erro, "prompt", None))
            problemas = _problemas_do_erro(erro)
            extraida = None
        evento.extra = {**comum, "problemas_validacao": problemas}
        if problemas:
            evento.erro = "RF14: estrutura inválida ou incoerente; fluxo bloqueado antes da minuta."
    if extraida is None or problemas:
        registro["problemas_validacao"] = problemas
        return _encerrar(config, auditoria, base, registro, "bloqueada")
    solicitacao = registro["solicitacao"] = extraida.valor

    with _etapa(auditoria, base, "d2_compreensao") as evento:
        try:
            ficha = nlp.compreender(texto, solicitacao, origem=origem, cliente=cliente, config=config, perfil=perfil)
            _anotar(evento, ficha.respostas, ficha.prompt)
            problemas = []
        except RespostaMalformada as erro:
            _anotar(evento, getattr(erro, "respostas", []), getattr(erro, "prompt", None))
            problemas = _problemas_do_erro(erro)
            ficha = None
            evento.erro = "RF15: ficha de compreensão inválida; fluxo bloqueado antes da minuta."
        evento.extra = {**comum, "categoria": solicitacao.categoria, "problemas_validacao": problemas}
    if ficha is None:
        registro["problemas_validacao"] = problemas
        return _encerrar(config, auditoria, base, registro, "bloqueada")
    registro["ficha"] = ficha.valor

    with _etapa(auditoria, base, "d2_recuperacao_geracao") as evento:
        info = indice.info()
        evento.extra = {
            **comum,
            "consulta": rag.consulta_da_solicitacao(solicitacao, config),
            "indice": {chave: info[chave] for chave in ("colecao", "modelo_embedding", "dimensao", "chunking", "versao_indice")},
        }
        try:
            gerada = rag.minuta_fundamentada(solicitacao, texto, indice=indice, cliente=cliente, config=config, perfil=perfil,
                                            auditoria=auditoria, id_execucao=id_execucao)
        except RespostaMalformada as erro:
            _anotar(evento, getattr(erro, "respostas", []), getattr(erro, "prompt", None))
            registro["problemas_validacao"] = _problemas_do_erro(erro)
            evento.extra["problemas_validacao"] = registro["problemas_validacao"]
            evento.erro = "RF19: minuta sem fundamento conferível; fluxo bloqueado."
            gerada = None
        if gerada is not None:
            _anotar(evento, gerada.respostas, gerada.prompt)
            resposta = gerada.valor
            decisoes = [*guardrails.verificar_trechos(resposta.trechos, config=config),
                        guardrails.verificar_saida(resposta, config=config)]
            registro["guardrails"].extend(decisoes)
            embeddings = indice.ultima_resposta
            evento.extra.update({
                "ids_recuperados": [t.trecho.id for t in resposta.trechos],
                "distancias": [round(t.distancia, 4) for t in resposta.trechos],
                "status_resposta": resposta.status,
                "fontes": resposta.fontes(),
                "tokens_embedding": embeddings.tokens_entrada if embeddings else None,
                "custo_embedding_usd": embeddings.custo_estimado_usd if embeddings else None,
                "guardrails": _decisoes(decisoes),
            })
    if gerada is None:
        return _encerrar(config, auditoria, base, registro, "bloqueada")
    if any(d.decisao == "bloquear" for d in registro["guardrails"]):
        # Saída bloqueada não fica gravada: pode conter justamente o que o guardrail barrou.
        return _encerrar(config, auditoria, base, registro, "bloqueada")
    revisar = any(d.decisao == "revisar" for d in registro["guardrails"])
    registro["resposta"] = resposta.model_copy(update={"necessita_revisao": resposta.necessita_revisao or revisar})
    return _encerrar(config, auditoria, base, registro, "pendente")


def _encerrar(config: Config, auditoria: Auditoria, base: dict, registro: dict, status: str) -> RegistroMinutaRAG:
    """Grava o registro (pendente ou bloqueada); nada é enviado ao cidadão."""
    final = RegistroMinutaRAG(**{**registro, "status": status})
    gravar_registro_rag(config, final)
    auditoria.registrar(
        Evento(
            **base, etapa="d2_registro", saida=config.relativo(caminho_registro_rag(config, final.id_execucao)),
            extra={"status": status, "necessita_revisao": bool(final.resposta and final.resposta.necessita_revisao),
                   "problemas_validacao": final.problemas_validacao},
        )
    )
    return final


def _anotar(evento: Evento, respostas: list[RespostaLLM], prompt: Prompt | None) -> None:
    """Tokens e custo somados de todas as chamadas da etapa (a correção do RF14 é uma segunda chamada)."""
    if respostas:
        evento.modelo = respostas[-1].modelo
        evento.parametros = {**respostas[-1].parametros, "chamadas": len(respostas)}
        evento.tokens_entrada = _soma([r.tokens_entrada for r in respostas])
        evento.tokens_saida = _soma([r.tokens_saida for r in respostas])
        evento.custo_estimado_usd = _soma([r.custo_estimado_usd for r in respostas])
    if prompt is not None:
        evento.versao_prompt = prompt.identificador
        evento.hash_prompt = prompt.hash


def _soma(valores: list) -> float | int | None:
    # Uma chamada sem a métrica deixa o total desconhecido, em vez de subestimado.
    if any(v is None for v in valores):
        return None
    total = sum(valores)
    return round(total, 6) if isinstance(total, float) else total


def _problemas_do_erro(erro: RespostaMalformada) -> list[str]:
    problemas = [str(erro)]
    if erro.detalhe:
        try:
            detalhe = json.loads(erro.detalhe)
        except json.JSONDecodeError:
            detalhe = [erro.detalhe]
        if not isinstance(detalhe, list):
            detalhe = [detalhe]
        problemas.extend(item if isinstance(item, str) else json.dumps(item, ensure_ascii=False) for item in detalhe)
    return problemas


def _decisoes(decisoes: list[DecisaoGuardrail]) -> list[dict]:
    return [d.model_dump() for d in decisoes]
