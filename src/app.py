"""Assistente de documentos (RF20): interface Streamlit local do Desafio 2.

Rodar com `python -m src.main assistente`. A interface só chama funções das
partes; regra de negócio não mora aqui. Cada consulta é independente: não há
memória conversacional (seção 1 do enunciado).
"""

from __future__ import annotations

import streamlit as st

from src import fluxo_rag, guardrails, ingestion, metrics, rag, revisao, sentiment
from src.audit import Auditoria
from src.config import CasoInexistente, carregar_config
from src.embeddings import IndiceVetorial
from src.entradas import ArquivoInvalido
from src.llm_client import ClienteLLM, ErroLLM
from src.tipos import PendenteDeImplementacao

NAO_LOCALIZADO = "não localizado"
EXPLICACAO_DISTANCIA = (
    "Distância de cosseno entre a pergunta e o trecho: 0 é idêntico, 2 é oposto. "
    "Menor distância é só proximidade de sentido, não garantia de que o trecho responde."
)


def executar(rotulo: str, funcao, *args, **kwargs):
    """Chama uma parte e traduz falhas em mensagens; devolve None quando não deu certo."""
    try:
        with st.spinner(rotulo):
            return funcao(*args, **kwargs)
    except PendenteDeImplementacao as erro:
        st.warning(f"Parte ainda não implementada: {erro}")
    except ErroLLM as erro:
        st.error(f"Erro do provedor: {erro}")
    except (ArquivoInvalido, CasoInexistente, revisao.RevisaoInvalida, ValueError, KeyError) as erro:
        st.error(f"Erro: {erro}")
    return None


def valor(campo):
    """null do contrato aparece como "não localizado" (RF14); lista vazia é só lista vazia."""
    return NAO_LOCALIZADO if campo is None or campo == "" else campo


def mostrar_registro(registro) -> None:
    st.subheader(f"Situação: {registro.status}")
    if registro.status == "bloqueada":
        st.error("Solicitação bloqueada antes da minuta; nada foi gerado.")
        for decisao in registro.guardrails:
            st.write(f"- {decisao.camada}: {decisao.decisao} ({decisao.regra}) — {decisao.motivo}")
        for problema in registro.problemas_validacao:
            st.write(f"- validação: {problema}")
        return
    if registro.solicitacao:
        st.markdown("**Ficha estruturada**")
        campos = registro.solicitacao.model_dump(exclude={"entidades"})
        st.table({campo: str(valor(v)) for campo, v in campos.items()})
        st.json(registro.solicitacao.entidades.model_dump())
    if registro.ficha:
        st.markdown(f"**Resumo:** {registro.ficha.resumo}")
        for inferencia in registro.ficha.inferencias:
            st.caption(f"Inferido — {inferencia.campo}: {inferencia.valor} ({inferencia.justificativa})")
    if registro.resposta:
        st.markdown(f"**Minuta — {registro.resposta.status}**")
        st.markdown(registro.resposta.resposta)
        with st.expander("Afirmações, fontes e trechos"):
            for afirmacao in registro.resposta.afirmacoes:
                st.write(f"- {afirmacao.texto} → {', '.join(afirmacao.fontes) or 'sem fonte'}")
            st.caption(EXPLICACAO_DISTANCIA)
            st.json([t.model_dump() for t in registro.resposta.trechos])
    for decisao in registro.guardrails:
        if decisao.decisao != "permitir":
            st.warning(f"Guardrail {decisao.camada}: {decisao.decisao} — {decisao.motivo}")
    if registro.decisao:
        st.info(f"Decisão: {registro.decisao.decisao} por {registro.decisao.revisor}: {registro.decisao.justificativa}")


st.set_page_config(page_title="Assistente de documentos", layout="wide")
config = carregar_config()
auditoria = Auditoria(config)

with st.sidebar:
    st.title("Assistente de documentos")
    st.caption("Desafio 2 — protótipo local. Nada é enviado ao cidadão.")
    perfis = list(config.dados["geracao"]["perfis"])
    perfil = st.selectbox("Perfil de geração", perfis, index=perfis.index(config.dados["geracao"]["perfil_ativo"]))
    st.caption(f"Modelo: {config.dados['geracao']['perfis'][perfil]['modelo']} · embeddings: {config.modelo('embeddings')}")
    chunkings = list(config.dados["indice"]["chunking"])
    chunking = st.selectbox("Configuração de chunking", chunkings, index=chunkings.index(config.dados["indice"]["chunking_ativo"]))
    tela = st.radio("Tela", ["Acervo e índice", "Solicitação", "Consulta ao acervo", "Avaliações"])

cliente = executar("Conectando ao provedor…", ClienteLLM, config)
indice = executar("Abrindo o índice…", IndiceVetorial, config, cliente, chunking=chunking) if cliente else None

if tela == "Acervo e índice":
    st.header("Acervo e índice")
    documentos = executar("Lendo o manifesto…", ingestion.ler_manifesto, config) or []
    if documentos:
        st.dataframe([d.model_dump(mode="json") for d in documentos], hide_index=True)
    else:
        st.info("Nenhum documento no manifesto (dados/acervo/acervo.json).")
    if indice:
        info = executar("Lendo o índice…", indice.info)
        if info:
            st.json(info)
        if documentos:
            desatualizados = executar("Comparando índice e acervo…", indice.desatualizados, documentos)
            if desatualizados:
                st.warning(f"Índice desatualizado para: {', '.join(desatualizados)}. Indexe de novo.")
        if st.button("Indexar o acervo", disabled=not documentos):
            for documento in documentos:
                total = executar(f"Indexando {documento.id}…", indice.indexar, documento)
                if total is not None:
                    st.write(f"{documento.id}: {total} trechos no índice.")
        with st.form("incluir"):
            st.markdown("**Incluir documento no acervo**")
            arquivo = st.file_uploader("Arquivo", type=[e.lstrip(".") for e in config.dados["acervo"]["extensoes"]])
            metadados = {campo: st.text_input(campo) for campo in ("id", "titulo", "versao", "tema")}
            if st.form_submit_button("Incluir") and arquivo:
                incluido = executar("Incluindo…", ingestion.incluir_documento, config, nome_arquivo=arquivo.name,
                                    conteudo=arquivo.getvalue(), metadados=metadados, auditoria=auditoria)
                if incluido:
                    st.success(f"{incluido.id} incluído. Indexe o acervo para que ele seja recuperado.")
        alvo = st.selectbox("Documento a excluir (acervo, índice e manifesto)", [d.id for d in documentos] or ["—"])
        if st.button("Excluir documento", disabled=not documentos):
            removido = executar(f"Excluindo {alvo}…", ingestion.excluir_documento, config, alvo, indice=indice, auditoria=auditoria)
            if removido:
                st.success(f"{alvo} excluído: {removido}")

elif tela == "Solicitação":
    st.header("Solicitação")
    texto = st.text_area("Texto da solicitação (fictícia)", height=200)
    if st.button("Analisar e gerar minuta", disabled=not (texto.strip() and indice)):
        st.session_state.pop("registro", None)
        # Um controle por execução: o teto de chamadas e tokens do RF16 vale para esta solicitação.
        cliente_execucao = ClienteLLM(config, controle=guardrails.ControleRecursos(config))
        registro = executar(
            "Processando…", fluxo_rag.processar_solicitacao, texto, origem="interface", config=config,
            cliente=cliente_execucao, indice=indice, auditoria=auditoria, perfil=perfil,
        )
        if registro:
            st.session_state["registro"] = registro
    registro = st.session_state.get("registro")
    if registro:
        mostrar_registro(registro)
        if registro.status == "pendente":
            with st.form("decisao"):
                decisao = st.radio("Decisão", ["aprovar", "rejeitar", "revisar"], horizontal=True)
                justificativa = st.text_area("Justificativa")
                revisor = st.text_input("Revisor")
                if st.form_submit_button("Registrar decisão"):
                    atualizado = executar("Registrando…", revisao.registrar_decisao_rag, config, auditoria, registro.id_execucao,
                                          decisao=decisao, justificativa=justificativa, revisor=revisor)
                    if atualizado:
                        st.session_state["registro"] = atualizado
                        st.success("Decisão registrada. Nada foi enviado ao cidadão.")

elif tela == "Consulta ao acervo":
    st.header("Consulta ao acervo")
    pergunta = st.text_input("Pergunta")
    top_k = st.slider("Top-k", 1, 10, config.dados["indice"]["top_k"])
    coluna_busca, coluna_resposta = st.columns(2)
    if coluna_busca.button("Buscar trechos", disabled=not (pergunta.strip() and indice)):
        trechos = executar("Buscando…", indice.buscar, pergunta, top_k=top_k)
        if trechos is not None:
            st.caption(EXPLICACAO_DISTANCIA)
            st.dataframe([{"distância": t.distancia, **t.trecho.model_dump()} for t in trechos], hide_index=True)
            if not trechos:
                st.info("Nenhum trecho encontrado: o índice está vazio ou desatualizado.")
    if coluna_resposta.button("Responder com fontes", disabled=not (pergunta.strip() and indice)):
        resultado = executar("Gerando…", rag.responder, pergunta, indice=indice, cliente=cliente, config=config, perfil=perfil)
        if resultado:
            resposta = resultado.valor
            st.subheader(resposta.status)
            st.markdown(resposta.resposta)
            for afirmacao in resposta.afirmacoes:
                st.write(f"- {afirmacao.texto} → {', '.join(afirmacao.fontes) or 'sem fonte'}")

else:
    st.header("Avaliações de atendimento")
    avaliacoes = executar("Lendo as avaliações…", sentiment.ler_avaliacoes, config) or []
    st.caption(f"{len(avaliacoes)} avaliações em dados/avaliacoes/{sentiment.ARQUIVO_AVALIACOES}.")
    if st.button("Classificar avaliações", disabled=not (avaliacoes and cliente)):
        resultados = executar("Classificando…", sentiment.classificar_lote, avaliacoes, cliente=cliente, config=config, perfil=perfil)
        if resultados:
            classificadas = [r.valor for r in resultados]
            st.dataframe([c.model_dump() for c in classificadas], hide_index=True)
            painel = executar("Agregando…", metrics.agregar_sentimentos, classificadas)
            if painel:
                st.json(painel)
            st.caption("A confiança declarada pelo modelo é estimativa não calibrada e não entra nas contagens.")
