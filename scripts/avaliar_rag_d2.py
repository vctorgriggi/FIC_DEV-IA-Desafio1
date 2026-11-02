"""Avaliação real do Estudante 2 contra os gabaritos D2-R01 a D2-R08 (chama a API).

python -m scripts.avaliar_rag_d2 chunking    # RF18/T07: A contra B nas cinco perguntas respondíveis
python -m scripts.avaliar_rag_d2 perguntas   # RF19/T08-T10: as oito perguntas no chunking ativo

Os ids de referência de cada pergunta são os trechos indexados que contêm o trecho literal do
gabarito (espaços normalizados); não são escritos à mão, porque mudam com o hash e o chunking.
Saída em resultados/metricas/, fora do git até a rodada final.
"""

from __future__ import annotations

import argparse
import json
import sys

from src import ingestion, metrics, rag
from src.config import carregar_config
from src.embeddings import IndiceVetorial
from src.llm_client import ClienteLLM, ErroLLM
from src.prompts import carregar_prompt


def _normal(texto: str) -> str:
    return " ".join(texto.split())


def _gabaritos(config) -> list[dict]:
    return [json.loads(c.read_text(encoding="utf-8")) for c in sorted(config.caminho("gabaritos").glob("D2-R*.json"))]


def _indexar(config, cliente, chunking: str) -> IndiceVetorial:
    indice = IndiceVetorial(config, cliente, chunking=chunking)
    for documento in ingestion.ler_manifesto(config):
        indice.indexar(documento)
    return indice


def _referencias(indice: IndiceVetorial, gabarito: dict) -> list[str]:
    dados = indice._colecao.get(include=["documents"])
    literais = [_normal(t["trecho_literal"]) for t in gabarito["trechos_referencia"]]
    return [i for i, texto in zip(dados["ids"], dados["documents"]) if any(l in _normal(texto) for l in literais)]


def chunking(config, cliente) -> dict:
    respondiveis = [g for g in _gabaritos(config) if g["tipo"] == "respondivel"]
    top_k = config.dados["indice"]["top_k"]
    resultado = {"modelo_embedding": config.modelo("embeddings"), "top_k": top_k, "configuracoes": {}}
    for nome, parametros in config.dados["indice"]["chunking"].items():
        indice = _indexar(config, cliente, nome)
        referencias = {g["id"]: _referencias(indice, g) for g in respondiveis}
        recuperados, distancias = {}, {}
        for gabarito in respondiveis:
            achados = indice.buscar(gabarito["pergunta"], top_k=top_k)
            recuperados[gabarito["id"]] = [a.trecho.id for a in achados]
            distancias[gabarito["id"]] = [round(a.distancia, 4) for a in achados]
        resultado["configuracoes"][nome] = {
            "parametros": parametros,
            "total_trechos": indice.contar(),
            "trechos_por_documento": _por_documento(indice),
            "referencias": referencias,
            "distancias": distancias,
            "acerto": metrics.acerto_recuperacao(recuperados, referencias),
        }
    return resultado


def _por_documento(indice: IndiceVetorial) -> dict:
    contagem: dict[str, int] = {}
    for metadados in indice._colecao.get(include=["metadatas"])["metadatas"]:
        contagem[metadados["documento_id"]] = contagem.get(metadados["documento_id"], 0) + 1
    return dict(sorted(contagem.items()))


def perguntas(config, cliente, perfil: str | None) -> dict:
    indice = _indexar(config, cliente, config.dados["indice"]["chunking_ativo"])
    prompt = carregar_prompt(config, "rag_d2", 1)
    resultado = {"perfil": config.perfil_geracao(perfil), "indice": indice.info(), "prompt": prompt.identificador,
                 "hash_prompt": prompt.hash, "perguntas": []}
    for gabarito in _gabaritos(config):
        item = {"id": gabarito["id"], "tipo": gabarito["tipo"], "status_esperado": gabarito["status_esperado"],
                "referencias": _referencias(indice, gabarito)}
        try:
            obtido = rag.responder(gabarito["pergunta"], indice=indice, cliente=cliente, config=config, perfil=perfil)
        except ErroLLM as erro:
            item.update(situacao="erro", erro=f"{type(erro).__name__}: {erro}", detalhe=erro.detalhe)
        else:
            resposta = obtido.valor
            item.update(
                situacao="obtido", status=resposta.status, resposta=resposta.resposta,
                afirmacoes=[a.model_dump() for a in resposta.afirmacoes],
                recuperados=[t.trecho.id for t in resposta.trechos],
                status_confere=resposta.status == gabarito["status_esperado"],
                cita_referencia=bool(set(resposta.fontes()) & set(item["referencias"])),
                tokens_entrada=sum(r.tokens_entrada or 0 for r in obtido.respostas),
                tokens_saida=sum(r.tokens_saida or 0 for r in obtido.respostas),
                custo_estimado_usd=round(sum(r.custo_estimado_usd or 0 for r in obtido.respostas), 6),
                chamadas=len(obtido.respostas),
            )
        resultado["perguntas"].append(item)
    obtidos = [p for p in resultado["perguntas"] if p["situacao"] == "obtido"]
    sem_resposta = [p for p in resultado["perguntas"] if p["tipo"] == "sem_resposta"]
    respondiveis = [p for p in obtidos if p["tipo"] == "respondivel"]
    resultado["metricas"] = {
        "status_confere": metrics.proporcao(sum(p["status_confere"] for p in obtidos), len(resultado["perguntas"])),
        "abstencao_correta": metrics.proporcao(sum(p.get("status") == "sem_evidencia" for p in sem_resposta), len(sem_resposta)),
        # Proxy por código: a afirmação cita o trecho do gabarito. A conferência de cada afirmação é humana (RF23).
        "respondiveis_citando_referencia": metrics.proporcao(
            sum(p["status"] == "fundamentada" and p["cita_referencia"] for p in respondiveis),
            sum(p["tipo"] == "respondivel" for p in resultado["perguntas"]),
        ),
        "contraditoria": [{k: p.get(k) for k in ("id", "status", "status_confere", "cita_referencia")}
                          for p in resultado["perguntas"] if p["tipo"] == "contraditoria"],
    }
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("etapa", choices=["chunking", "perguntas"])
    parser.add_argument("--perfil", default=None, help="perfil de geração (perguntas); padrão: o ativo")
    args = parser.parse_args(argv)
    config = carregar_config()
    cliente = ClienteLLM(config)
    resultado = chunking(config, cliente) if args.etapa == "chunking" else perguntas(config, cliente, args.perfil)
    sufixo = f"-{args.perfil}" if args.perfil else ""
    destino = config.caminho("metricas") / f"rag-d2-{args.etapa}{sufixo}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resultado.get("metricas") or {k: v["acerto"] for k, v in resultado["configuracoes"].items()},
                     ensure_ascii=False, indent=2))
    print(f"Gravado em {config.relativo(destino)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
