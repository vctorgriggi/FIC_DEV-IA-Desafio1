"""Demonstração real de T06, T12 e T14 numa cópia temporária do projeto (chama a API só para consultas).

python -m scripts.demonstrar_indice_d2 [--saida caminho.json]

A cópia leva config, prompts, acervo e o índice já construído; acervo e índice reais ficam intactos.
T06 reabre o índice em outro processo (o Chroma reaproveita o cliente dentro do mesmo processo, o que
não provaria reinício).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
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
    """SDK que registra e recusa qualquer uso: a contagem prova que reabrir e reindexar não gastam embeddings."""

    def __init__(self):
        self.tentativas: list[str] = []

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        self.tentativas.append(nome)
        raise AssertionError(f"Chamada inesperada ao provedor: {nome}")


class _ClienteContado(ClienteLLM):
    textos_embedding = 0

    def gerar_embeddings(self, *, modelo, textos):
        self.textos_embedding += len(textos)
        return super().gerar_embeddings(modelo=modelo, textos=textos)


def reabrir_em_outro_processo(raiz: Path, dados: dict) -> dict:
    """Roda em processo novo: abre o índice, reindexa o acervo com um cliente que recusa chamadas e conta."""
    config = Config(dados, raiz)
    sdk = _SemChamada()
    indice = IndiceVetorial(config, ClienteLLM(config, chave="sem-uso", sdk=sdk))
    total = indice.contar()
    documentos = ingestion.ler_manifesto(config)
    for documento in documentos:
        indice.indexar(documento)
    return {"trechos_apos_reabrir": total, "trechos_apos_reindexar": indice.contar(),
            "chamadas_ao_provedor_na_reindexacao": len(sdk.tentativas), "versao_indice": indice.info()["versao_indice"],
            "desatualizados": indice.desatualizados(documentos)}


def _copia(config: Config, destino: Path) -> Config:
    for pasta in ("prompts", config.dados["caminhos"]["acervo"], config.dados["caminhos"]["indice"]):
        if (config.raiz / pasta).exists():
            shutil.copytree(config.raiz / pasta, destino / pasta)
    return Config(deepcopy(config.dados), destino)


def demonstrar(config: Config) -> dict:
    with tempfile.TemporaryDirectory() as pasta:
        copia = _copia(config, Path(pasta))
        auditoria = Auditoria(copia)
        real = _ClienteContado(copia)
        documentos = ingestion.ler_manifesto(copia)
        construido = IndiceVetorial(copia, real)
        for documento in documentos:
            construido.indexar(documento)
        antes = construido.info()

        # T06: outro processo abre o mesmo diretório; reindexar o mesmo acervo não duplica nem chama o provedor.
        processo = subprocess.run(
            [sys.executable, "-m", "scripts.demonstrar_indice_d2", "--reabrir", str(copia.raiz), json.dumps(copia.dados)],
            cwd=config.raiz, capture_output=True, text=True, check=True,
        )
        reaberto = json.loads(processo.stdout.strip().splitlines()[-1])
        versao_reaberta = reaberto.pop("versao_indice")
        t06 = {"trechos_antes": antes["total_trechos"], "processo": "novo (subprocess)", **reaberto,
               "versao_indice_igual": versao_reaberta == antes["versao_indice"]}

        # T12 (troca): o perfil alternativo responde sobre o mesmo índice; só a consulta passa pelo embedding.
        textos_antes = real.textos_embedding
        troca = rag.responder("Qual é o horário de atendimento?", indice=construido, cliente=real, config=copia,
                              perfil="alternativo")
        t12_troca = {"modelo": troca.respostas[-1].modelo if troca.respostas else None, "status": troca.valor.status,
                     "textos_embedados": real.textos_embedding - textos_antes,
                     "trechos_no_indice_antes_e_depois": [antes["total_trechos"], construido.contar()]}

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
                "T06": t06, "T12_troca": t12_troca, "T12_falha": t12, "T14": t14}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", default=None)
    parser.add_argument("--reabrir", nargs=2, metavar=("RAIZ", "CONFIG_JSON"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.reabrir:
        print(json.dumps(reabrir_em_outro_processo(Path(args.reabrir[0]), json.loads(args.reabrir[1]))))
        return 0
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
