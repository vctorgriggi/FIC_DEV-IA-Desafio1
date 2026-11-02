"""Avaliação real do Estudante 2 contra os gabaritos D2-R01 a D2-R08 (chama a API).

python -m scripts.avaliar_rag_d2 chunking    # RF18/T07: A contra B nas cinco perguntas respondíveis
python -m scripts.avaliar_rag_d2 perguntas   # RF19/T08-T10: as oito perguntas no chunking ativo
python -m scripts.avaliar_rag_d2 perguntas --chunking B --perfil alternativo
python -m scripts.avaliar_rag_d2 variante    # D2-R08-neutra: o conflito sem as datas na pergunta

Os ids de referência de cada pergunta são os trechos indexados que contêm o trecho literal do
gabarito (espaços normalizados); não são escritos à mão, porque mudam com o hash e o chunking.
Saída em resultados/metricas/, fora do git até a rodada final. Cada pergunta vira um evento
"d2_consulta" em resultados/logs/execucoes.jsonl (RF21), com o id_execucao gravado na saída.
As perguntas vão ao rag.responder, sem as camadas de entrada e saída do fluxo: a avaliação mede a
recuperação e a geração. O filtro de trechos (rag.separar_trechos) se aplica.
"""

from __future__ import annotations

import argparse
import json
import sys

from src import ingestion, metrics, rag
from src.audit import Auditoria, agora_iso, novo_id
from src.config import carregar_config
from src.embeddings import IndiceVetorial
from src.fluxo import _etapa
from src.fluxo_rag import _anotar
from src.llm_client import ClienteLLM, ErroLLM
from src.prompts import carregar_prompt


class ClienteContado(ClienteLLM):
    """Conta os textos enviados ao embedding: zero na indexação prova que o índice foi reaproveitado."""

    textos_embedding = 0

    def gerar_embeddings(self, *, modelo, textos):
        self.textos_embedding += len(textos)
        return super().gerar_embeddings(modelo=modelo, textos=textos)


def _normal(texto: str) -> str:
    return " ".join(texto.split())


def _gabaritos(config) -> list[dict]:
    """As oito perguntas oficiais, na lista do catálogo do Integrante 1 (variantes ficam fora)."""
    catalogo = json.loads((config.caminho("originais") / "desafio-2" / "casos.json").read_text(encoding="utf-8"))
    return [json.loads((config.raiz / caminho).read_text(encoding="utf-8")) for caminho in catalogo["perguntas"]]


def _indexar(config, cliente, chunking: str) -> IndiceVetorial:
    indice = IndiceVetorial(config, cliente, chunking=chunking)
    for documento in ingestion.ler_manifesto(config):
        indice.indexar(documento)
    return indice


def _referencias(indice: IndiceVetorial, gabarito: dict) -> list[str]:
    # Só no documento que o gabarito indica: DOC-01 repete frases do DOC-02, mas foi substituído.
    dados = indice._colecao.get(include=["documents", "metadatas"])
    return [
        i for i, texto, metadados in zip(dados["ids"], dados["documents"], dados["metadatas"])
        if any(r["documento_id"] == metadados["documento_id"] and _normal(r["trecho_literal"]) in _normal(texto)
               for r in gabarito["trechos_referencia"])
    ]


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


def perguntas(config, cliente, perfil: str | None, chunking_nome: str | None = None, gabaritos: list[dict] | None = None) -> dict:
    antes = getattr(cliente, "textos_embedding", None)
    indice = _indexar(config, cliente, chunking_nome or config.dados["indice"]["chunking_ativo"])
    prompt = carregar_prompt(config, "rag_d2", 1)
    auditoria = Auditoria(config)
    resultado = {"perfil": config.perfil_geracao(perfil), "indice": indice.info(), "prompt": prompt.identificador,
                 "hash_prompt": prompt.hash, "perguntas": [],
                 "textos_embedados_na_indexacao": None if antes is None else cliente.textos_embedding - antes}
    for gabarito in gabaritos or _gabaritos(config):
        item = {"id": gabarito["id"], "tipo": gabarito["tipo"], "status_esperado": gabarito["status_esperado"],
                "referencias": _referencias(indice, gabarito), "id_execucao": novo_id(), "executado_em": agora_iso()}
        base = {"id_execucao": item["id_execucao"], "caso_id": gabarito["id"], "modalidade": "pergunta_d2"}
        try:
            with _etapa(auditoria, base, "d2_consulta") as evento:
                evento.extra = {"consulta": rag.minimizar(gabarito["pergunta"], config), "perfil_geracao": resultado["perfil"]["nome"],
                                "versao_indice": resultado["indice"]["versao_indice"], "chunking": indice.chunking}
                try:
                    obtido = rag.responder(gabarito["pergunta"], indice=indice, cliente=cliente, config=config, perfil=perfil)
                except ErroLLM as erro:
                    _anotar(evento, getattr(erro, "respostas", []), getattr(erro, "prompt", None))
                    raise
                _anotar(evento, obtido.respostas, obtido.prompt)
                evento.extra.update(ids_recuperados=[t.trecho.id for t in obtido.valor.trechos],
                                    status_resposta=obtido.valor.status, fontes=obtido.valor.fontes())
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
    parser.add_argument("etapa", choices=["chunking", "perguntas", "variante"])
    parser.add_argument("--perfil", default=None, help="perfil de geração (perguntas); padrão: o ativo")
    parser.add_argument("--chunking", default=None, help="índice A ou B (perguntas); padrão: o ativo")
    args = parser.parse_args(argv)
    config = carregar_config()
    cliente = ClienteContado(config)
    if args.etapa == "chunking":
        resultado = chunking(config, cliente)
    else:
        variante = [json.loads((config.caminho("gabaritos") / "D2-R08-neutra.json").read_text(encoding="utf-8"))]
        resultado = perguntas(config, cliente, args.perfil, args.chunking, variante if args.etapa == "variante" else None)
    sufixo = "".join(f"-{v}" for v in (args.chunking, args.perfil) if v)
    destino = config.caminho("metricas") / f"rag-d2-{args.etapa}{sufixo}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resultado.get("metricas") or {k: v["acerto"] for k, v in resultado["configuracoes"].items()},
                     ensure_ascii=False, indent=2))
    print(f"Gravado em {config.relativo(destino)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
