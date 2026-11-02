"""Índice vetorial persistente do acervo (RF17, RF24), sobre o Chroma.

Os vetores vêm de ClienteLLM.gerar_embeddings com config["modelos"]["embeddings"];
trocar esse modelo exige reindexar. Trocar o perfil de geração não toca o índice (RF21).
"""

from __future__ import annotations

import hashlib
import json

import chromadb
from chromadb.config import Settings

from .config import Config
from .ingestion import caminho_documento, dividir, extrair_texto
from .llm_client import ClienteLLM, RespostaEmbeddings
from .privacidade import mascarar, ocultar_segredos
from .revisao import hash_arquivo
from .schemas import DocumentoAcervo, Trecho, TrechoRecuperado


class IndiceIncompativel(ValueError):
    """Índice gravado com outro modelo de embedding: vetores de espaços diferentes não se comparam."""


class IndiceVetorial:
    """Uma coleção Chroma por chunking (A ou B), com distância de cosseno.

    `chunking` é uma chave de config["indice"]["chunking"], não o perfil de geração.
    Os metadados da coleção guardam modelo e dimensão do embedding.
    """

    def __init__(self, config: Config, cliente: ClienteLLM, *, chunking: str | None = None):
        chunking = chunking or config.dados["indice"]["chunking_ativo"]
        if chunking not in config.dados["indice"]["chunking"]:
            raise KeyError(f"Chunking '{chunking}' não existe. Opções: {', '.join(config.dados['indice']['chunking'])}.")
        self.config = config
        self.cliente = cliente
        self.chunking = chunking
        self.modelo = config.modelo("embeddings")
        # Última chamada de embeddings (indexação ou busca), para a auditoria do fluxo (RF21).
        self.ultima_resposta: RespostaEmbeddings | None = None
        self._cliente_chroma = chromadb.PersistentClient(
            path=str(config.caminho("indice")), settings=Settings(anonymized_telemetry=False)
        )
        self._colecao = self._cliente_chroma.get_or_create_collection(
            self._nome(chunking),
            # O espaço vai em configuration: no Chroma 1.x, "hnsw:space" em metadata impede modify() depois.
            configuration={"hnsw": {"space": "cosine"}},
            metadata={"modelo_embedding": self.modelo},
            embedding_function=None,
        )
        gravado = (self._colecao.metadata or {}).get("modelo_embedding")
        if gravado != self.modelo:
            raise IndiceIncompativel(
                f"Índice {self._colecao.name} foi gerado com {gravado} e o config pede {self.modelo}. "
                f"Apague a pasta {config.relativo(config.caminho('indice'))} e indexe o acervo de novo."
            )

    def indexar(self, documento: DocumentoAcervo) -> int:
        """Extrai, divide e grava os trechos do documento; devolve quantos trechos dele ficaram no índice.

        Mesmo arquivo e mesma versão não chamam o provedor de novo; arquivo mudado apaga os trechos antigos (T06).
        """
        trechos = dividir(documento, extrair_texto(documento, config=self.config), perfil=self.chunking, config=self.config)
        novos = {t.id for t in trechos}
        gravados = self._colecao.get(where={"documento_id": documento.id}, include=["metadatas"])
        versoes = {m.get("versao") for m in gravados["metadatas"]}
        if set(gravados["ids"]) == novos and versoes == {documento.versao}:
            return len(novos)
        orfaos = [i for i in gravados["ids"] if i not in novos]
        if orfaos:
            self._colecao.delete(ids=orfaos)
        resposta = self.cliente.gerar_embeddings(modelo=self.modelo, textos=[self._seguro(t.texto) for t in trechos])
        self.ultima_resposta = resposta
        self._registrar_dimensao(resposta.dimensao)
        self._colecao.upsert(
            ids=[t.id for t in trechos],
            embeddings=resposta.vetores,
            documents=[t.texto for t in trechos],
            metadatas=[_metadados(t) for t in trechos],
        )
        return len(trechos)

    def buscar(self, consulta: str, *, top_k: int | None = None) -> list[TrechoRecuperado]:
        """Top-k por distância de cosseno (top_k padrão em config["indice"]["top_k"]); índice vazio dá lista vazia."""
        top_k = top_k or self.config.dados["indice"]["top_k"]
        total = self._colecao.count()
        if not consulta.strip() or total == 0:
            return []
        resposta = self.cliente.gerar_embeddings(modelo=self.modelo, textos=[self._seguro(consulta)])
        self.ultima_resposta = resposta
        dimensao = (self._colecao.metadata or {}).get("dimensao")
        if dimensao is not None and dimensao != resposta.dimensao:
            raise IndiceIncompativel(f"A consulta tem dimensão {resposta.dimensao} e o índice, {dimensao}. Reindexe o acervo.")
        achados = self._colecao.query(
            query_embeddings=resposta.vetores,
            n_results=min(top_k, total),
            include=["documents", "metadatas", "distances"],
        )
        return [
            TrechoRecuperado(trecho=_trecho(identificador, texto, metadados), distancia=float(distancia))
            for identificador, texto, metadados, distancia in zip(
                achados["ids"][0], achados["documents"][0], achados["metadatas"][0], achados["distances"][0]
            )
        ]

    def excluir(self, documento_id: str) -> int:
        """Remove os trechos do documento de todas as coleções de chunking; devolve quantos saíram."""
        existentes = {c.name for c in self._cliente_chroma.list_collections()}
        removidos = 0
        for chunking in self.config.dados["indice"]["chunking"]:
            if self._nome(chunking) not in existentes:
                continue
            colecao = self._cliente_chroma.get_collection(self._nome(chunking), embedding_function=None)
            ids = colecao.get(where={"documento_id": documento_id})["ids"]
            if ids:
                colecao.delete(ids=ids)
                removidos += len(ids)
        return removidos

    def contar(self) -> int:
        return self._colecao.count()

    def info(self) -> dict:
        """Modelo e dimensão do embedding, chunking, total de trechos e {documento_id: {versao, hash}} indexados.

        `versao_indice` resume modelo, chunking e documentos: muda quando qualquer um deles muda (RF21).
        """
        metadados = self._colecao.get(include=["metadatas"])["metadatas"]
        documentos = {
            m["documento_id"]: {"versao": m["versao"], "hash": m["hash_documento"]}
            for m in sorted(metadados, key=lambda m: m["documento_id"])
        }
        parametros = self.config.dados["indice"]["chunking"][self.chunking]
        assinatura = json.dumps([self.modelo, self.chunking, parametros, documentos], sort_keys=True)
        return {
            "colecao": self._colecao.name,
            "modelo_embedding": self.modelo,
            "dimensao": (self._colecao.metadata or {}).get("dimensao"),
            "chunking": self.chunking,
            "parametros_chunking": parametros,
            "distancia": "cosseno",
            "total_trechos": len(metadados),
            "documentos": documentos,
            "versao_indice": hashlib.sha256(assinatura.encode("utf-8")).hexdigest()[:12],
        }

    def desatualizados(self, documentos: list[DocumentoAcervo]) -> list[str]:
        """Ids do manifesto ausentes do índice ou com versão ou hash diferentes do arquivo atual (RF20)."""
        indexados = self.info()["documentos"]
        desatualizados = []
        for documento in documentos:
            gravado = indexados.get(documento.id)
            arquivo = caminho_documento(self.config, documento)
            atual = hash_arquivo(arquivo) if arquivo.is_file() else None
            if gravado is None or gravado["versao"] != documento.versao or gravado["hash"] != atual:
                desatualizados.append(documento.id)
        return desatualizados

    def _nome(self, chunking: str) -> str:
        return f"{self.config.dados['indice']['colecao']}_{chunking}"

    def _seguro(self, texto: str) -> str:
        """O que sai para o provedor de embeddings passa pela mesma minimização da geração (RF24)."""
        return ocultar_segredos(mascarar(texto, self.config.dados["privacidade"]["mascarar_antes_de_enviar"])[0], [])

    def _registrar_dimensao(self, dimensao: int) -> None:
        metadados = dict(self._colecao.metadata or {})
        if metadados.get("dimensao") is None:
            self._colecao.modify(metadata={**metadados, "dimensao": dimensao})
        elif metadados["dimensao"] != dimensao:
            raise IndiceIncompativel(f"Embedding com dimensão {dimensao} num índice de dimensão {metadados['dimensao']}. Reindexe.")


def _metadados(trecho: Trecho) -> dict:
    # O Chroma descarta metadado None; pagina e secao voltam ausentes e Trecho os aceita assim.
    return {chave: valor for chave, valor in trecho.model_dump(exclude={"id", "texto"}).items() if valor is not None}


def _trecho(identificador: str, texto: str, metadados: dict) -> Trecho:
    return Trecho(id=identificador, texto=texto, **metadados)
