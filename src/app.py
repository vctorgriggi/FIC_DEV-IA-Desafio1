"""Assistente de documentos (RF20): interface Streamlit local do Desafio 2.

Rodar com `python -m src.main assistente`. A interface só chama funções das
partes; regra de negócio não mora aqui. Cada consulta é independente: não há
memória conversacional (seção 1 do enunciado).
"""

from __future__ import annotations

import json

import streamlit as st

from src import fluxo_rag, ingestion, metrics, rag, revisao, sentiment
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
    return NAO_LOCALIZADO if campo in (None, "", []) else campo


st.set_page_config(page_title="Assistente de documentos", layout="wide")
config = carregar_config()
auditoria = Auditoria(config)

with st.sidebar:
    st.title("Assistente de documentos")
    st.caption("Desafio 2 — protótipo local. Nada é enviado ao cidadão.")
    perfis = list(config.dados["geracao"]["perfis"])
    perfil = st.selectbox("Perfil de geração", perfis, index=perfis.index(config.dados["geracao"]["perfil_ativo"]))
    st.caption(f"Modelo: {config.perfil_geracao(perfil)['modelo']} · embeddings: {config.modelo('embeddings')}")
    chunkings = list(config.dados["indice"]["chunking"])
    chunking = st.selectbox("Configuração de chunking", chunkings, index=chunkings.index(config.dados["indice"]["chunking_ativo"]))
    tela = st.radio("Tela", ["Acervo e índice", "Solicitação", "Consulta ao acervo", "Avaliações"])

cliente = executar("Conectando ao provedor…", ClienteLLM, config)
indice = IndiceVetorial(config, cliente, perfil=chunking) if cliente else None

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
        if st.button("Indexar o acervo", disabled=not documentos):
            for documento in documentos:
                total = executar(f"Indexando {documento.id}…", indice.indexar, documento)
                if total is not None:
                    st.write(f"{documento.id}: {total} trechos no índice.")
        alvo = st.selectbox("Documento a excluir do índice", [d.id for d in documentos] or ["—"])
        if st.button("Excluir do índice", disabled=not documentos):
            removidos = executar(f"Excluindo {alvo}…", indice.excluir, alvo)
            if removidos is not None:
                st.success(f"{removidos} trechos de {alvo} removidos do índice.")

elif tela == "Solicitação":
    st.header("Solicitação")
    texto = st.text_area("Texto da solicitação (fictícia)", height=200)
    if st.button("Analisar e gerar minuta", disabled=not (texto.strip() and indice)):
        registro = executar(
            "Processando…", fluxo_rag.processar_solicitacao, texto,
            origem="interface", config=config, cliente=cliente, indice=indice, auditoria=auditoria, perfil=perfil,
        )
        if registro:
            st.session_state["registro"] = registro
    registro = st.session_state.get("registro")
    if registro:
        st.subheader("Ficha estruturada")
        st.table({campo: str(valor(v)) for campo, v in registro.get("solicitacao", {}).items()})
        ficha = registro.get("ficha") or {}
        st.markdown(f"**Resumo:** {valor(ficha.get('resumo'))}  \n**Categoria:** {valor(ficha.get('categoria'))}")
        resposta = registro.get("resposta") or {}
        st.subheader(f"Minuta — {resposta.get('status', NAO_LOCALIZADO)}")
        st.markdown(resposta.get("resposta") or NAO_LOCALIZADO)
        with st.expander("Fontes e trechos"):
            st.caption(EXPLICACAO_DISTANCIA)
            st.json(resposta.get("trechos", []))
        with st.form("decisao"):
            decisao = st.radio("Decisão", ["aprovar", "rejeitar", "revisar"], horizontal=True)
            justificativa = st.text_area("Justificativa")
            revisor = st.text_input("Revisor")
            if st.form_submit_button("Registrar decisão"):
                if executar("Registrando…", revisao.registrar_decisao_rag, config, auditoria, registro.get("id_execucao", ""),
                            decisao=decisao, justificativa=justificativa, revisor=revisor):
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
        resposta = executar("Gerando…", rag.responder, pergunta, indice=indice, cliente=cliente, config=config, perfil=perfil)
        if resposta:
            st.subheader(resposta.status)
            st.markdown(resposta.resposta)
            st.write("Fontes:", resposta.fontes)

else:
    st.header("Avaliações de atendimento")
    arquivo = config.caminho("avaliacoes") / "avaliacoes.json"
    avaliacoes = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.is_file() else []
    st.caption(f"{len(avaliacoes)} avaliações em {config.relativo(arquivo)}.")
    if st.button("Classificar avaliações", disabled=not (avaliacoes and cliente)):
        resultados = []
        for item in avaliacoes:
            resultado = executar(f"Classificando {item['id']}…", sentiment.classificar, item["id"], item["texto"],
                                 cliente=cliente, config=config)
            if resultado is None:
                break
            resultados.append(resultado)
        if resultados:
            painel = executar("Agregando…", metrics.agregar_sentimentos, resultados)
            st.dataframe([r.model_dump() for r in resultados], hide_index=True)
            if painel:
                st.json(painel)
            st.caption("A confiança declarada pelo modelo é estimativa não calibrada e não entra nas contagens.")
