"""Demonstração real de T06, T12 (falha) e T14 numa cópia temporária do projeto (chama a API só para consultas).

python -m scripts.demonstrar_indice_d2 [--saida caminho.json]

A cópia leva config, prompts, acervo e o índice já construído; acervo e índice reais ficam intactos.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

from src import ingestion, rag
from src.audit import Auditoria
from src.config import Config, carregar_config
from src.embeddings import IndiceVetorial
from src.fluxo import _etapa
from src.llm_client import ClienteLLM, ErroLLM


class _SemChamada:
    """SDK que falha se for chamado: prova que reabrir e reindexar não gastam embeddings."""

    def __getattr__(self, nome):
        raise AssertionError(f"Chamada inesperada ao provedor: {nome}")


def _copia(config: Config, destino: Path) -> Config:
    for pasta in ("prompts", config.dados["caminhos"]["acervo"], config.dados["caminhos"]["indice"]):
        if (config.raiz / pasta).exists():
            shutil.copytree(config.raiz / pasta, destino / pasta)
    return Config(deepcopy(config.dados), destino)


def demonstrar(config: Config) -> dict:
    with tempfile.TemporaryDirectory() as pasta:
        copia = _copia(config, Path(pasta))
        auditoria = Auditoria(copia)
        real = ClienteLLM(copia)
        documentos = ingestion.ler_manifesto(copia)
        construido = IndiceVetorial(copia, real)
        for documento in documentos:
            construido.indexar(documento)
        antes = construido.info()

        # T06: outro processo abre o mesmo diretório; reindexar o mesmo acervo não duplica nem chama o provedor.
        reaberto = IndiceVetorial(copia, ClienteLLM(copia, chave="sem-uso", sdk=_SemChamada()))
        total_reaberto = reaberto.contar()
        for documento in documentos:
            reaberto.indexar(documento)
        t06 = {
            "trechos_antes": antes["total_trechos"], "trechos_apos_reabrir": total_reaberto,
            "trechos_apos_reindexar": reaberto.contar(), "chamadas_ao_provedor_na_reindexacao": 0,
            "versao_indice_igual": reaberto.info()["versao_indice"] == antes["versao_indice"],
            "desatualizados": reaberto.desatualizados(documentos),
        }

        # T12 (falha): perfil com modelo inexistente; o erro vira ErroLLM auditado e o índice não muda.
        copia.dados["geracao"]["perfis"]["falha_demonstracao"] = {"provedor": copia.dados["provedor"], "modelo": "modelo-inexistente-d2"}
        base = {"id_execucao": "demo-t12", "caso_id": "D2-R05", "modalidade": "pergunta_d2"}
        erro = None
        try:
            with _etapa(auditoria, base, "d2_resposta"):
                rag.responder("Qual é o horário de atendimento?", indice=construido, cliente=real, config=copia,
                              perfil="falha_demonstracao")
        except ErroLLM as falha:
            erro = f"{type(falha).__name__}: {falha}"
        [evento] = auditoria.eventos(id_execucao="demo-t12")
        t12 = {"erro_tratado": erro, "evento_auditoria": {k: evento[k] for k in ("etapa", "erro", "duracao_s")},
               "versao_indice_igual": construido.info()["versao_indice"] == antes["versao_indice"]}

        # T14: exclusão de DOC-05 no acervo, no manifesto e em todas as coleções.
        consulta = "Qual é o horário de atendimento do balcão acadêmico?"
        antes_busca = [a.trecho.documento_id for a in construido.buscar(consulta)]
        outro = IndiceVetorial(copia, real, chunking="A")
        for documento in documentos:
            outro.indexar(documento)
        removido = ingestion.excluir_documento(copia, "DOC-05", indice=construido, auditoria=auditoria)
        depois_busca = [a.trecho.documento_id for a in construido.buscar(consulta)]
        t14 = {
            "consulta": consulta, "documentos_no_top_k_antes": antes_busca, "documentos_no_top_k_depois": depois_busca,
            "removido": removido,
            "DOC-05_no_manifesto": "DOC-05" in {d.id for d in ingestion.ler_manifesto(copia)},
            "DOC-05_em_A": "DOC-05" in outro.info()["documentos"], "DOC-05_em_B": "DOC-05" in construido.info()["documentos"],
            "evento_auditoria": auditoria.eventos(etapa="acervo_exclusao")[0]["extra"],
        }
        return {"indice": {k: antes[k] for k in ("modelo_embedding", "dimensao", "chunking", "parametros_chunking",
                                                   "total_trechos", "versao_indice")},
                "T06": t06, "T12_falha": t12, "T14": t14}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", default=None)
    args = parser.parse_args(argv)
    config = carregar_config()
    resultado = demonstrar(config)
    destino = Path(args.saida) if args.saida else config.caminho("metricas") / "rag-d2-demonstracao.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
    print(f"Gravado em {config.relativo(destino)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
