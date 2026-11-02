"""Geração fundamentada no acervo (RF19): resposta ou minuta com citações, abstenção ou conflito.

Recuperação e geração ficam separadas para que o fluxo aplique o guardrail de trechos entre as duas
(RF16): trecho bloqueado não chega ao modelo. O modelo recebe só os trechos, cada um delimitado como
dado não confiável. O que ele devolve passa por conferência local, com no máximo uma tentativa de
correção (mesma regra do RF14): fonte fora dos trechos, status sem fonte e número que não está nas
fontes citadas são erro.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import ValidationError

from . import guardrails
from .config import Config
from .embeddings import IndiceVetorial
from .entradas import ArquivoInvalido
from .ingestion import ler_manifesto
from .llm_client import ClienteLLM, ErroLLM, RespostaMalformada, formato_json
from .nlp import PADRAO_DATA
from .privacidade import mascarar, ocultar_segredos
from .prompts import Prompt, carregar_prompt, delimitar
from .schemas import DecisaoGuardrail, RespostaGerada, RespostaRAG, SolicitacaoEstruturada, TrechoRecuperado
from .tipos import Resultado

_NUMERO = re.compile(r"\d+")
# Do caso, só data e protocolo podem aparecer numa afirmação institucional: "ouvi que são 45 dias" não vira regra.
_DATA_OU_PROTOCOLO = re.compile(PADRAO_DATA.pattern + r"|\b\d{4}-\d{6}\b", re.IGNORECASE)


def minimizar(texto: str, config: Config) -> str:
    """Texto que sai para o provedor ou para o log: dados pessoais mascarados e formato de chave ocultado."""
    return ocultar_segredos(mascarar(texto, config.dados["privacidade"]["mascarar_antes_de_enviar"])[0], [])


def consulta_da_solicitacao(solicitacao: SolicitacaoEstruturada, config: Config) -> str:
    """Consulta ao índice montada de assunto e pedido, já minimizada; vazia quando os dois são null."""
    return minimizar(" ".join(p for p in (solicitacao.assunto, solicitacao.pedido) if p), config).strip()


def recuperar(consulta: str, *, indice: IndiceVetorial, config: Config, top_k: int | None = None) -> list[TrechoRecuperado]:
    """Top-k do índice para a consulta já minimizada; consulta vazia não busca."""
    consulta = minimizar(consulta, config).strip()
    return indice.buscar(consulta, **({'top_k': top_k} if top_k is not None else {})) if consulta else []


def responder(
    pergunta: str,
    *,
    indice: IndiceVetorial,
    cliente: ClienteLLM,
    config: Config,
    perfil: str | None = None,
    top_k: int | None = None,
) -> Resultado[RespostaRAG]:
    """Resposta a uma pergunta avulsa, sem registro: usada na avaliação do RF19.

    Aplica o guardrail de trechos; entrada, registro para decisão humana e auditoria ficam em fluxo_rag.consultar.
    """
    usados, decisoes = separar_trechos(recuperar(pergunta, indice=indice, config=config, top_k=top_k), config=config)
    return _revisar_se_suspeito(gerar_resposta(pergunta, usados, cliente=cliente, config=config, perfil=perfil), decisoes)


def gerar_resposta(
    pergunta: str, trechos: list[TrechoRecuperado], *, cliente: ClienteLLM, config: Config, perfil: str | None = None
) -> Resultado[RespostaRAG]:
    prompt = carregar_prompt(config, "rag_d2", 1)
    if not trechos:
        return Resultado(_sem_trechos("O acervo indexado não trouxe trecho para esta pergunta. O caso segue para o operador."), [], prompt)
    consulta = minimizar(pergunta, config)
    entrada = "\n".join([prompt.texto, delimitar(consulta, "pergunta"), _contexto(trechos, config)])
    return _gerar(entrada, trechos, caso=consulta, modo="pergunta", prompt=prompt, cliente=cliente, config=config, perfil=perfil)


def minuta_fundamentada(
    solicitacao: SolicitacaoEstruturada,
    texto_original: str,
    *,
    indice: IndiceVetorial,
    cliente: ClienteLLM,
    config: Config,
    perfil: str | None = None,
) -> Resultado[RespostaRAG]:
    """Minuta para revisão humana: fatos do caso só da solicitação, orientação só do acervo, em blocos separados."""
    recuperados = recuperar(consulta_da_solicitacao(solicitacao, config), indice=indice, config=config)
    usados, decisoes = separar_trechos(recuperados, config=config)
    resultado = gerar_minuta(solicitacao, texto_original, usados, cliente=cliente, config=config, perfil=perfil)
    return _revisar_se_suspeito(resultado, decisoes)


def gerar_minuta(
    solicitacao: SolicitacaoEstruturada,
    texto_original: str,
    trechos: list[TrechoRecuperado],
    *,
    cliente: ClienteLLM,
    config: Config,
    perfil: str | None = None,
) -> Resultado[RespostaRAG]:
    """O texto original não vai ao modelo; serve só para aceitar número que a minuta repete do caso."""
    prompt = carregar_prompt(config, "minuta_rag_d2", 1)
    if not consulta_da_solicitacao(solicitacao, config):
        return Resultado(_sem_trechos(
            "A solicitação não traz assunto nem pedido identificáveis, então não há orientação do acervo a aplicar. "
            "O servidor precisa pedir esclarecimento ao cidadão."), [], prompt)
    if not trechos:
        return Resultado(_sem_trechos(
            "O acervo indexado não trouxe orientação para este pedido. O caso segue para análise do servidor."), [], prompt)
    caso = minimizar(solicitacao.model_dump_json(), config)
    entrada = "\n".join([prompt.texto, delimitar(caso, "solicitacao"), _contexto(trechos, config)])
    resultado = _gerar(entrada, trechos, caso=caso + " " + minimizar(texto_original, config), modo="minuta",
                       prompt=prompt, cliente=cliente, config=config, perfil=perfil)
    if solicitacao.necessita_revisao:
        resultado.valor = resultado.valor.model_copy(update={"necessita_revisao": True})
    return resultado


def separar_trechos(
    recuperados: list[TrechoRecuperado], *, config: Config
) -> tuple[list[TrechoRecuperado], list[DecisaoGuardrail]]:
    """RF16 entre recuperação e geração: os trechos que podem ir ao modelo e uma decisão por trecho recuperado.

    Trecho suspeito tira do contexto o documento inteiro, não só o trecho.
    """
    decisoes = guardrails.verificar_trechos(recuperados, config=config) if recuperados else []
    suspeitos = {t.trecho.documento_id for t, d in zip(recuperados, decisoes) if d.decisao != "permitir"}
    return [t for t in recuperados if t.trecho.documento_id not in suspeitos], decisoes


def _revisar_se_suspeito(resultado: Resultado[RespostaRAG], decisoes: list[DecisaoGuardrail]) -> Resultado[RespostaRAG]:
    if any(d.decisao != "permitir" for d in decisoes):
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
    caso: str,
    modo: Literal["pergunta", "minuta"],
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
        problemas = _problemas(gerada, trechos, caso=caso, modo=modo)
        if not problemas:
            candidata = RespostaRAG(**gerada.model_dump(), trechos=trechos, necessita_revisao=gerada.status != 'fundamentada')
            decisao = guardrails.verificar_saida(candidata, config=config)
            if decisao.decisao == 'bloquear':
                problemas.append('RF16: saída bloqueada pela regra ' + decisao.regra + '.')
        if not problemas:
            valor = RespostaRAG(**gerada.model_dump(), trechos=trechos, necessita_revisao=gerada.status != "fundamentada")
            return Resultado(valor, respostas, prompt)
    erro = RespostaMalformada("RF19: resposta sem fundamento conferível após uma tentativa de correção.",
                              detalhe=json.dumps(problemas, ensure_ascii=False))
    erro.respostas, erro.prompt = respostas, prompt
    raise erro


def _problemas(gerada: RespostaGerada, trechos: list[TrechoRecuperado], *, caso: str, modo: Literal["pergunta", "minuta"]) -> list[str]:
    """Conferência por código do que o modelo devolveu; cada problema diz a regra, não o conteúdo.

    Número numa afirmação com fonte precisa estar nos trechos que ela cita (ou ser data/protocolo do caso).
    Na resposta, precisa estar em algum trecho citado ou no caso: data/protocolo da pergunta; qualquer
    número da solicitação na minuta, que pode repetir fatos do caso. Paráfrase sem número passa por aqui
    e fica para a revisão humana.
    """
    # Sem o id do trecho: os dígitos do hash não são números da fonte.
    textos = {
        t.trecho.id: " ".join(str(v) for v in (t.trecho.documento_id, t.trecho.versao, t.trecho.pagina, t.trecho.secao, t.trecho.texto) if v)
        for t in trechos
    }
    datas_do_caso = _numeros(" ".join(m.group() for m in _DATA_OU_PROTOCOLO.finditer(caso)))
    numeros_do_caso = _numeros(caso) if modo == "minuta" else datas_do_caso
    problemas = []
    if not gerada.resposta.strip():
        problemas.append("resposta vazia.")
    if ocultar_segredos(gerada.resposta, []) != gerada.resposta:
        problemas.append("resposta reproduz formato de credencial.")
    citadas: set[str] = set()
    for numero, afirmacao in enumerate(gerada.afirmacoes, 1):
        estranhas = [f for f in afirmacao.fontes if f not in textos]
        if estranhas:
            problemas.append(f"afirmação {numero}: cita {len(estranhas)} fonte(s) fora dos trechos recuperados.")
        validas = [f for f in afirmacao.fontes if f in textos]
        citadas.update(validas)
        if modo == "pergunta" and gerada.status != "sem_evidencia" and not afirmacao.fontes:
            problemas.append(f"afirmação {numero}: sem fonte.")
        # Afirmação sem fonte na minuta é fato do caso; com fonte, é orientação institucional.
        apoio = _numeros(" ".join(textos[f] for f in validas)) | (datas_do_caso if validas else numeros_do_caso)
        if _numeros(afirmacao.texto) - apoio:
            problemas.append(f"afirmação {numero}: número ou data ausente das fontes citadas.")
    if _numeros(gerada.resposta) - (_numeros(" ".join(textos[f] for f in citadas)) | numeros_do_caso):
        problemas.append("resposta: número ou data ausente das fontes citadas e do caso.")
    if gerada.status in ("fundamentada", "conflito") and not citadas:
        problemas.append(f"status {gerada.status} sem nenhuma fonte citada.")
    return problemas


def _numeros(texto: str) -> set[str]:
    # "08" e "8" são o mesmo número numa hora ou data.
    return {numero.lstrip("0") or "0" for numero in _NUMERO.findall(texto)}
