"""Geração fundamentada no acervo (RF19): resposta ou minuta com citações, abstenção ou conflito.

O modelo recebe só os trechos recuperados, cada um delimitado como dado não confiável. O que ele
devolve passa por conferência local: fonte fora dos trechos, status sem fonte e número ou data que
não aparece nas fontes são erro, com no máximo uma tentativa de correção (mesma regra do RF14).
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from .config import Config
from .embeddings import IndiceVetorial
from .entradas import ArquivoInvalido
from .ingestion import ler_manifesto
from .llm_client import ClienteLLM, ErroLLM, RespostaMalformada, formato_json
from .privacidade import mascarar, ocultar_segredos
from .prompts import Prompt, carregar_prompt, delimitar
from .schemas import RespostaGerada, RespostaRAG, SolicitacaoEstruturada, TrechoRecuperado
from .tipos import Resultado

_NUMERO = re.compile(r"\d+")


def minimizar(texto: str, config: Config) -> str:
    """Texto que sai para o provedor ou para o log: dados pessoais mascarados e formato de chave ocultado."""
    return ocultar_segredos(mascarar(texto, config.dados["privacidade"]["mascarar_antes_de_enviar"])[0], [])


def consulta_da_solicitacao(solicitacao: SolicitacaoEstruturada, config: Config) -> str:
    """Consulta ao índice montada de assunto e pedido, já minimizada; vazia quando os dois são null."""
    return minimizar(" ".join(p for p in (solicitacao.assunto, solicitacao.pedido) if p), config).strip()


def responder(
    pergunta: str,
    *,
    indice: IndiceVetorial,
    cliente: ClienteLLM,
    config: Config,
    perfil: str | None = None,
) -> Resultado[RespostaRAG]:
    """Resposta a uma pergunta avulsa, com status e citação por afirmação; sem trecho, abstém-se sem chamar o modelo."""
    prompt = carregar_prompt(config, "rag_d2", 1)
    consulta = minimizar(pergunta, config)
    trechos = indice.buscar(consulta)
    if not trechos:
        return Resultado(_sem_trechos("O acervo indexado não trouxe trecho para esta pergunta. O caso segue para o operador."), [], prompt)
    entrada = "\n".join([prompt.texto, delimitar(consulta, "pergunta"), _contexto(trechos, config)])
    return _gerar(entrada, trechos, permitido=consulta, fonte_em_todas=True, prompt=prompt,
                  cliente=cliente, config=config, perfil=perfil)


def minuta_fundamentada(
    solicitacao: SolicitacaoEstruturada,
    texto_original: str,
    *,
    indice: IndiceVetorial,
    cliente: ClienteLLM,
    config: Config,
    perfil: str | None = None,
) -> Resultado[RespostaRAG]:
    """Minuta para revisão humana: fatos do caso só da solicitação, orientação só do acervo, em blocos separados.

    O texto original não vai ao modelo; serve só para aceitar número ou data que a minuta repete do caso.
    """
    prompt = carregar_prompt(config, "minuta_rag_d2", 1)
    consulta = consulta_da_solicitacao(solicitacao, config)
    if not consulta:
        return Resultado(_sem_trechos(
            "A solicitação não traz assunto nem pedido identificáveis, então não há orientação do acervo a aplicar. "
            "O servidor precisa pedir esclarecimento ao cidadão."), [], prompt)
    trechos = indice.buscar(consulta)
    if not trechos:
        return Resultado(_sem_trechos(
            "O acervo indexado não trouxe orientação para este pedido. O caso segue para análise do servidor."), [], prompt)
    caso = minimizar(solicitacao.model_dump_json(), config)
    entrada = "\n".join([prompt.texto, delimitar(caso, "solicitacao"), _contexto(trechos, config)])
    resultado = _gerar(entrada, trechos, permitido=caso + " " + minimizar(texto_original, config), fonte_em_todas=False,
                       prompt=prompt, cliente=cliente, config=config, perfil=perfil)
    if solicitacao.necessita_revisao:
        resultado.valor = resultado.valor.model_copy(update={"necessita_revisao": True})
    return resultado


def _sem_trechos(texto: str) -> RespostaRAG:
    return RespostaRAG(status="sem_evidencia", resposta=texto, afirmacoes=[], trechos=[], necessita_revisao=True)


def _contexto(trechos: list[TrechoRecuperado], config: Config) -> str:
    """Cabeçalho de cada trecho vem do manifesto (confiável); o texto do trecho vai delimitado."""
    try:
        manifesto = {d.id: d for d in ler_manifesto(config)}
    except ArquivoInvalido:
        manifesto = {}
    blocos = []
    for recuperado in trechos:
        trecho = recuperado.trecho
        documento = manifesto.get(trecho.documento_id)
        cabecalho = [f"Trecho id={trecho.id}", f"documento={trecho.documento_id} ({trecho.titulo})", f"versão={trecho.versao}"]
        if documento and documento.vigencia_inicio:
            cabecalho.append(f"vigência desde {documento.vigencia_inicio.isoformat()}")
        if documento and documento.substitui:
            cabecalho.append(f"substitui {', '.join(documento.substitui)}")
        if trecho.pagina is not None:
            cabecalho.append(f"página {trecho.pagina}")
        if trecho.secao:
            cabecalho.append(f"seção {trecho.secao}")
        blocos.append("; ".join(cabecalho) + "\n" + delimitar(minimizar(trecho.texto, config), f"acervo/{trecho.documento_id}"))
    return "Trechos do acervo:\n" + "\n".join(blocos)


def _gerar(
    entrada: str,
    trechos: list[TrechoRecuperado],
    *,
    permitido: str,
    fonte_em_todas: bool,
    prompt: Prompt,
    cliente: ClienteLLM,
    config: Config,
    perfil: str | None,
) -> Resultado[RespostaRAG]:
    geracao = config.perfil_geracao(perfil)
    formato = formato_json(RespostaGerada.model_json_schema(), "resposta_rag")
    sistema = carregar_prompt(config, "sistema_seguro_d2", 1).texto
    respostas = []
    problemas: list = []
    for tentativa in range(2):
        correcao = "" if not tentativa else (
            "\nCorrija uma única vez estes problemas da resposta anterior:\n"
            + delimitar(json.dumps(problemas, ensure_ascii=False), "diagnostico_validacao")
        )
        try:
            resposta = cliente.gerar(modelo=geracao["modelo"], entrada=entrada + correcao, instrucao_sistema=sistema,
                                     formato_resposta=formato, parametros=geracao.get("parametros", {}))
        except ErroLLM as erro:
            erro.respostas, erro.prompt = respostas, prompt
            raise
        respostas.append(resposta)
        try:
            gerada = RespostaGerada.model_validate_json(resposta.texto)
        except ValidationError as erro:
            # Só tipo e local do erro: a saída inválida é conteúdo não confiável e não volta ao modelo.
            problemas = [{"type": e["type"], "loc": list(e["loc"])} for e in erro.errors()]
            continue
        problemas = _problemas(gerada, trechos, permitido=permitido, fonte_em_todas=fonte_em_todas)
        if not problemas:
            valor = RespostaRAG(**gerada.model_dump(), trechos=trechos, necessita_revisao=gerada.status != "fundamentada")
            return Resultado(valor, respostas, prompt)
    erro = RespostaMalformada("RF19: resposta sem fundamento conferível após uma tentativa de correção.",
                              detalhe=json.dumps(problemas, ensure_ascii=False))
    erro.respostas, erro.prompt = respostas, prompt
    raise erro


def _problemas(gerada: RespostaGerada, trechos: list[TrechoRecuperado], *, permitido: str, fonte_em_todas: bool) -> list[str]:
    """Conferência por código do que o modelo devolveu; cada problema diz a regra, não o conteúdo."""
    # Id, versão e página citados na resposta também contam como apoio, não como número inventado.
    textos = {
        t.trecho.id: " ".join(str(v) for v in (t.trecho.id, t.trecho.versao, t.trecho.pagina, t.trecho.secao, t.trecho.texto) if v)
        for t in trechos
    }
    problemas = []
    if not gerada.resposta.strip():
        problemas.append("resposta vazia.")
    if ocultar_segredos(gerada.resposta, []) != gerada.resposta:
        problemas.append("resposta reproduz formato de credencial.")
    for numero, afirmacao in enumerate(gerada.afirmacoes, 1):
        estranhas = [f for f in afirmacao.fontes if f not in textos]
        if estranhas:
            problemas.append(f"afirmação {numero}: cita {len(estranhas)} fonte(s) fora dos trechos recuperados.")
        if fonte_em_todas and gerada.status != "sem_evidencia" and not afirmacao.fontes:
            problemas.append(f"afirmação {numero}: sem fonte.")
        apoio = " ".join(textos[f] for f in afirmacao.fontes if f in textos) + " " + permitido
        if _numeros(afirmacao.texto) - _numeros(apoio):
            problemas.append(f"afirmação {numero}: número ou data ausente das fontes citadas.")
    if _numeros(gerada.resposta) - _numeros(" ".join(textos.values()) + " " + permitido):
        problemas.append("resposta: número ou data ausente dos trechos e do caso.")
    citadas = {f for a in gerada.afirmacoes for f in a.fontes if f in textos}
    if gerada.status in ("fundamentada", "conflito") and not citadas:
        problemas.append(f"status {gerada.status} sem nenhuma fonte citada.")
    return problemas


def _numeros(texto: str) -> set[str]:
    # "08" e "8" são o mesmo número numa hora ou data.
    return {numero.lstrip("0") or "0" for numero in _NUMERO.findall(texto)}
