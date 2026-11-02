"""Fluxo integrado do Desafio 2 (seção 9 do enunciado): solicitação até minuta fundamentada pendente.

Entrada e proteção -> Compreensão -> Recuperação e geração -> minuta "pendente" para revisão.
A interface chama só este módulo, as funções de leitura das partes e o revisao.py.

Três portas, uma mesma saída (RegistroMinutaRAG em resultados/minutas_rag/, decidido pelo operador):
- processar_solicitacao: texto digitado;
- processar_caso: caso do Desafio 1 (texto, áudio ou imagem), cuja transcrição ou OCR vira a solicitação;
- consultar: pergunta avulsa ao acervo, sem extração (RF19), também registrada para decisão humana.
"""

from __future__ import annotations

import json
from typing import Callable

from . import audio, guardrails, nlp, rag, vision
from .audit import Auditoria, Evento, agora_iso, novo_id
from .config import Config
from .embeddings import IndiceVetorial
from .entradas import validar_arquivo
from .fluxo import _etapa
from .llm_client import ClienteLLM, ErroLLM, RespostaLLM, RespostaMalformada
from .prompts import Prompt
from .revisao import caminho_registro_rag, gravar_registro_rag
from .schemas import ESQUEMA_VERSAO, DecisaoGuardrail, RegistroMinutaRAG, RespostaRAG, TrechoRecuperado
from .tipos import Resultado

ETAPA_GERACAO = "d2_recuperacao_geracao"


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
    cliente, indice = _preparar_execucao(config, cliente, indice)
    return _processar(texto, origem=origem, config=config, cliente=cliente, indice=indice, auditoria=auditoria,
                      perfil=perfil, id_execucao=novo_id(), previas=[])


def processar_caso(
    caso_id: str,
    *,
    config: Config,
    cliente: ClienteLLM,
    indice: IndiceVetorial,
    auditoria: Auditoria,
    perfil: str | None = None,
) -> RegistroMinutaRAG:
    """Seção 1 do enunciado: texto, áudio e imagem do Desafio 1 alimentam o mesmo fluxo de extração.

    Áudio e imagem passam pela transcrição (RF06) ou pelo OCR (RF08) e o texto revisado segue como solicitação.
    Trecho incerto na transcrição vira decisão "revisar": a minuta sai marcada para conferência.
    """
    cliente, indice = _preparar_execucao(config, cliente, indice)
    caso = config.caso(caso_id)
    id_execucao = novo_id()
    base = {"id_execucao": id_execucao, "caso_id": caso_id, "modalidade": caso["modalidade"], "arquivo_origem": caso["arquivo"]}
    with _etapa(auditoria, base, "d2_extracao_texto") as evento:
        arquivo = validar_arquivo(config.raiz / caso["arquivo"], caso["modalidade"], config)
        incertos: list[str] = []
        if caso["modalidade"] == "texto":
            texto = arquivo.caminho.read_text(encoding="utf-8")
        else:
            extrator = audio.transcrever if caso["modalidade"] == "audio" else vision.extrair_texto
            try:
                extraido = extrator(arquivo, cliente=cliente, config=config)
            except ErroLLM as erro:
                _anotar(evento, getattr(erro, "respostas", []), getattr(erro, "prompt", None))
                raise
            _anotar(evento, [extraido.resposta] if extraido.resposta else [], extraido.prompt)
            texto, incertos = extraido.texto_revisado, extraido.trechos_incertos
        evento.extra = {"sha256": arquivo.sha256, "trechos_incertos": len(incertos)}
    previas = [DecisaoGuardrail(
        decisao="revisar", camada="entrada", regra="transcricao_incerta",
        motivo=f"{len(incertos)} trecho(s) incerto(s) na transcrição ou no OCR; conferir antes de aprovar.",
    )] if incertos else []
    return _processar(texto, origem=caso_id, config=config, cliente=cliente, indice=indice, auditoria=auditoria,
                      perfil=perfil, id_execucao=id_execucao, previas=previas)


def consultar(
    pergunta: str,
    *,
    config: Config,
    cliente: ClienteLLM,
    indice: IndiceVetorial,
    auditoria: Auditoria,
    perfil: str | None = None,
    top_k: int | None = None,
) -> RegistroMinutaRAG:
    """Pergunta avulsa ao acervo com as mesmas camadas da solicitação e o mesmo registro para decisão humana.

    Sem extração nem ficha: `solicitacao` e `ficha` ficam None e `entrada` guarda a pergunta minimizada.
    """
    cliente, indice = _preparar_execucao(config, cliente, indice)
    id_execucao = novo_id()
    base = {"id_execucao": id_execucao, "caso_id": "consulta", "modalidade": "consulta_d2"}
    registro = _registro_inicial(pergunta, origem="consulta", config=config, perfil=perfil, id_execucao=id_execucao)
    comum = _comum(config, perfil)
    with _etapa(auditoria, base, "d2_entrada") as evento:
        decisao = guardrails.verificar_entrada(pergunta, config=config)
        registro["guardrails"].append(decisao)
        evento.extra = {**comum, "guardrails": _decisoes([decisao])}
    if decisao.decisao == "bloquear":
        return _encerrar(config, auditoria, base, registro, "bloqueada")
    return _recuperar_gerar_e_encerrar(
        rag.minimizar(pergunta, config),
        lambda trechos: rag.gerar_resposta(pergunta, trechos, cliente=cliente, config=config, perfil=perfil),
        config=config, indice=indice, auditoria=auditoria, base=base, registro=registro, comum=comum,
        top_k=top_k,
    )


def _preparar_execucao(config, cliente, indice):
    if cliente.controle is None:
        cliente = cliente.nova_execucao(guardrails.ControleRecursos(config))
    return cliente, indice.com_cliente(cliente)


def modelo_da_minuta(auditoria: Auditoria, id_execucao: str) -> str | None:
    """Modelo que gerou a minuta, lido da auditoria (RF21, RF24): o registro guarda o perfil, não o modelo."""
    eventos = auditoria.eventos(id_execucao=id_execucao, etapa=ETAPA_GERACAO)
    return next((e["modelo"] for e in reversed(eventos) if e.get("modelo")), None)


def _processar(
    texto: str,
    *,
    origem: str,
    config: Config,
    cliente: ClienteLLM,
    indice: IndiceVetorial,
    auditoria: Auditoria,
    perfil: str | None,
    id_execucao: str,
    previas: list[DecisaoGuardrail],
) -> RegistroMinutaRAG:
    base = {"id_execucao": id_execucao, "caso_id": rag.minimizar(origem, config), "modalidade": "solicitacao_d2"}
    comum = _comum(config, perfil)
    registro = _registro_inicial(texto, origem=origem, config=config, perfil=perfil, id_execucao=id_execucao)
    registro["guardrails"].extend(previas)

    with _etapa(auditoria, base, "d2_entrada") as evento:
        decisao = guardrails.verificar_entrada(texto, config=config)
        registro["guardrails"].append(decisao)
        evento.extra = {**comum, "guardrails": _decisoes(registro["guardrails"])}
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
        except ErroLLM as erro:
            _anotar(evento, getattr(erro, "respostas", []), getattr(erro, "prompt", None))
            raise
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
        except ErroLLM as erro:
            _anotar(evento, getattr(erro, "respostas", []), getattr(erro, "prompt", None))
            raise
        evento.extra = {**comum, "categoria": solicitacao.categoria, "problemas_validacao": problemas}
    if ficha is None:
        registro["problemas_validacao"] = problemas
        return _encerrar(config, auditoria, base, registro, "bloqueada")
    registro["ficha"] = ficha.valor

    return _recuperar_gerar_e_encerrar(
        rag.consulta_da_solicitacao(solicitacao, config),
        lambda trechos: rag.gerar_minuta(solicitacao, texto, trechos, cliente=cliente, config=config, perfil=perfil),
        config=config, indice=indice, auditoria=auditoria, base=base, registro=registro, comum=comum,
    )


def _recuperar_gerar_e_encerrar(
    consulta: str,
    gerar: Callable[[list[TrechoRecuperado]], Resultado[RespostaRAG]],
    *,
    config: Config,
    indice: IndiceVetorial,
    auditoria: Auditoria,
    base: dict,
    registro: dict,
    comum: dict,
    top_k: int | None = None,
) -> RegistroMinutaRAG:
    """Recupera, aplica o guardrail de trechos ANTES da geração (trecho bloqueado não vai ao modelo), gera e confere a saída."""
    with _etapa(auditoria, base, ETAPA_GERACAO) as evento:
        info = indice.info()
        evento.extra = {
            **comum,
            "consulta": consulta,
            "indice": {chave: info[chave] for chave in ("colecao", "modelo_embedding", "dimensao", "chunking", "versao_indice")},
        }
        recuperados = rag.recuperar(consulta, indice=indice, config=config, top_k=top_k) if consulta else []
        usados, decisoes_trechos = rag.separar_trechos(recuperados, config=config)
        registro["guardrails"].extend(decisoes_trechos)
        embeddings = indice.ultima_resposta
        evento.extra.update({
            "ids_recuperados": [t.trecho.id for t in recuperados],
            "distancias": [round(t.distancia, 4) for t in recuperados],
            "ids_enviados_ao_modelo": [t.trecho.id for t in usados],
            "tokens_embedding": embeddings.tokens_entrada if embeddings else None,
            "custo_embedding_usd": embeddings.custo_estimado_usd if embeddings else None,
        })
        try:
            gerada = gerar(usados)
        except RespostaMalformada as erro:
            _anotar(evento, getattr(erro, "respostas", []), getattr(erro, "prompt", None))
            registro["problemas_validacao"] = _problemas_do_erro(erro)
            evento.extra["problemas_validacao"] = registro["problemas_validacao"]
            evento.erro = "RF19: resposta sem fundamento conferível; fluxo bloqueado."
            gerada = None
        except ErroLLM as erro:
            _anotar(evento, getattr(erro, "respostas", []), getattr(erro, "prompt", None))
            raise
        if gerada is not None:
            _anotar(evento, gerada.respostas, gerada.prompt)
            resposta = gerada.valor
            saida = guardrails.verificar_saida(resposta, config=config)
            registro["guardrails"].append(saida)
            evento.extra.update({
                "status_resposta": resposta.status,
                "fontes": resposta.fontes(),
                "guardrails": _decisoes([*decisoes_trechos, saida]),
            })
    if gerada is None or any(d.decisao == "bloquear" for d in registro["guardrails"] if d.camada != "trechos"):
        # Saída bloqueada não fica gravada: pode conter justamente o que o guardrail barrou.
        return _encerrar(config, auditoria, base, registro, "bloqueada")
    revisar = any(d.decisao != "permitir" for d in registro["guardrails"])
    registro["resposta"] = resposta.model_copy(update={"necessita_revisao": resposta.necessita_revisao or revisar})
    return _encerrar(config, auditoria, base, registro, "pendente")


def _comum(config: Config, perfil: str | None) -> dict:
    geracao = config.perfil_geracao(perfil)
    return {"esquema_versao": ESQUEMA_VERSAO, "perfil_geracao": geracao["nome"], "modelo_geracao": geracao["modelo"]}


def _registro_inicial(texto: str, *, origem: str, config: Config, perfil: str | None, id_execucao: str) -> dict:
    return {
        "id_execucao": id_execucao, "status": "pendente", "criado_em": agora_iso(), "origem": origem,
        "esquema_versao": ESQUEMA_VERSAO, "perfil_geracao": config.perfil_geracao(perfil)["nome"],
        # O registro guarda a entrada minimizada, a mesma que o provedor recebeu.
        "entrada": rag.minimizar(texto, config),
        "guardrails": [], "problemas_validacao": [], "solicitacao": None, "ficha": None, "resposta": None, "decisao": None,
    }


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
