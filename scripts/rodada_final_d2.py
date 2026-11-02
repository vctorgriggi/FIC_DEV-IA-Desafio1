"""Rodada real do fluxo integrado do Desafio 2 (chama a API), sobre o índice e o acervo do projeto.

python -m scripts.rodada_final_d2              # fluxo e consultas
python -m scripts.rodada_final_d2 consultas    # só as oito perguntas

- D2-S01 a D2-S06 por fluxo_rag.processar_solicitacao: guardrails, extração, ficha, recuperação e minuta;
- D2-A01 e D2-A03 pela mesma porta (ataque na solicitação); D2-A02 por fluxo_rag.consultar, com uma
  pergunta que recupera o DOC-06 (ataque no acervo);
- texto-01 e imagem-01 do Desafio 1 por fluxo_rag.processar_caso (seção 1: mesmas entradas, mesmo fluxo).

Cada execução grava um RegistroMinutaRAG em resultados/minutas_rag/ (pendente ou bloqueada, sem decisão:
a decisão é do operador, na tela) e eventos em resultados/logs/execucoes.jsonl. O resumo, com a conferência
contra os gabaritos, vai para resultados/metricas/rodada-final-d2.json e rodada-final-d2-consultas.json.
As oito perguntas oficiais (D2-R01 a D2-R08) passam por fluxo_rag.consultar e também viram registros.
"""

from __future__ import annotations

import argparse
import json
import sys

from src import fluxo_rag, guardrails
from src.audit import Auditoria, agora_iso
from src.config import carregar_config
from src.embeddings import IndiceVetorial
from src.llm_client import ClienteLLM
from src import ingestion

PERGUNTA_A02 = "Quais são as orientações do anexo de atendimento?"


def _normal(texto: str) -> str:
    return " ".join(texto.split())


def _recursos(auditoria: Auditoria, id_execucao: str) -> dict:
    eventos = auditoria.eventos(id_execucao=id_execucao)
    custo = sum((e.get("custo_estimado_usd") or 0) + ((e.get("extra") or {}).get("custo_embedding_usd") or 0) for e in eventos)
    return {
        "etapas": [e["etapa"] for e in eventos],
        "tokens_entrada": sum((e.get("tokens_entrada") or 0) + ((e.get("extra") or {}).get("tokens_embedding") or 0) for e in eventos),
        "tokens_saida": sum(e.get("tokens_saida") or 0 for e in eventos),
        "custo_estimado_usd": round(custo, 6),
        "erros": [e["erro"] for e in eventos if e.get("erro")],
    }


def _resumo(registro, auditoria: Auditoria) -> dict:
    resposta = registro.resposta
    return {
        "id_execucao": registro.id_execucao,
        "origem": registro.origem,
        "status": registro.status,
        "guardrails": [f"{d.camada}:{d.decisao}:{d.regra}" for d in registro.guardrails],
        "problemas_validacao": registro.problemas_validacao,
        "categoria": registro.solicitacao.categoria if registro.solicitacao else None,
        "status_resposta": resposta.status if resposta else None,
        "necessita_revisao": resposta.necessita_revisao if resposta else None,
        "fontes": resposta.fontes() if resposta else [],
        "ids_recuperados_no_registro": [t.trecho.id for t in resposta.trechos] if resposta else [],
        **_recursos(auditoria, registro.id_execucao),
    }


def _conferir_solicitacao(linha: dict, registro, gabarito: dict) -> dict:
    esperada = gabarito["solicitacao_esperada"]
    citados = [t.trecho for t in registro.resposta.trechos if t.trecho.id in linha["fontes"]] if registro.resposta else []
    referencias = [
        f for f in gabarito["fontes_esperadas"]
        if any(t.documento_id == f["documento_id"] and _normal(f["trecho_referencia"]) in _normal(t.texto) for t in citados)
    ]
    return {
        "categoria_esperada": esperada["categoria"],
        "categoria_igual": linha["categoria"] == esperada["categoria"],
        "fontes_esperadas_citadas": f"{len(referencias)}/{len(gabarito['fontes_esperadas'])}",
        "decisao_esperada": gabarito["decisao_esperada"],
        "marcada_para_revisao": bool(linha["necessita_revisao"]),
    }


def _fluxo(config, auditoria, indice, cliente, catalogo) -> dict:
    saida = {"solicitacoes": [], "ataques": [], "casos_desafio_1": []}
    for caminho in catalogo["solicitacoes"]:
        gabarito = json.loads((config.raiz / caminho).read_text(encoding="utf-8"))
        texto = (config.raiz / gabarito["arquivo"]).read_text(encoding="utf-8")
        registro = fluxo_rag.processar_solicitacao(texto, origem=gabarito["caso_id"], config=config, cliente=cliente(),
                                                   indice=indice, auditoria=auditoria)
        linha = _resumo(registro, auditoria)
        linha["conferencia"] = _conferir_solicitacao(linha, registro, gabarito)
        saida["solicitacoes"].append(linha)
        print(gabarito["caso_id"], registro.status, linha["status_resposta"], linha["conferencia"])

    for caminho in catalogo["ataques"]:
        gabarito = json.loads((config.raiz / caminho).read_text(encoding="utf-8"))
        if gabarito["alvo"] == "acervo":
            registro = fluxo_rag.consultar(PERGUNTA_A02, config=config, cliente=cliente(), indice=indice, auditoria=auditoria)
            evento = auditoria.eventos(id_execucao=registro.id_execucao, etapa=fluxo_rag.ETAPA_GERACAO)[-1]["extra"]
            linha = {**_resumo(registro, auditoria), "pergunta": PERGUNTA_A02,
                     "ids_recuperados": evento["ids_recuperados"], "ids_enviados_ao_modelo": evento["ids_enviados_ao_modelo"]}
        else:
            registro = fluxo_rag.processar_solicitacao(gabarito["entrada"], origem=gabarito["id"], config=config,
                                                       cliente=cliente(), indice=indice, auditoria=auditoria)
            linha = _resumo(registro, auditoria)
        linha.update({"id": gabarito["id"], "alvo": gabarito["alvo"], "decisao_esperada": gabarito["decisao_esperada"]})
        saida["ataques"].append(linha)
        print(gabarito["id"], registro.status, linha["guardrails"])

    for caso_id in ("texto-01", "imagem-01"):
        registro = fluxo_rag.processar_caso(caso_id, config=config, cliente=cliente(), indice=indice, auditoria=auditoria)
        linha = _resumo(registro, auditoria)
        saida["casos_desafio_1"].append(linha)
        print(caso_id, registro.status, linha["status_resposta"], linha["categoria"])
    return saida


def _consultas(config, auditoria, indice, cliente, catalogo) -> dict:
    """As oito perguntas oficiais pela porta da interface: cada uma vira registro pendente para decisão."""
    saida = {"consultas": []}
    for caminho in catalogo["perguntas"]:
        gabarito = json.loads((config.raiz / caminho).read_text(encoding="utf-8"))
        registro = fluxo_rag.consultar(gabarito["pergunta"], config=config, cliente=cliente(), indice=indice, auditoria=auditoria)
        linha = {"id": gabarito["id"], "status_esperado": gabarito["status_esperado"], **_resumo(registro, auditoria)}
        linha["status_confere"] = linha["status_resposta"] == gabarito["status_esperado"]
        saida["consultas"].append(linha)
        print(gabarito["id"], registro.status, linha["status_resposta"], linha["status_confere"])
    return saida


PARTES = {"fluxo": (_fluxo, "rodada-final-d2.json"), "consultas": (_consultas, "rodada-final-d2-consultas.json")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("partes", nargs="*", help=f"{' e '.join(PARTES)} (padrão: todas)")
    args = parser.parse_args()
    args.partes = args.partes or list(PARTES)
    if set(args.partes) - set(PARTES):
        parser.error(f"partes possíveis: {', '.join(PARTES)}")
    config = carregar_config()
    auditoria = Auditoria(config)
    base = ClienteLLM(config)
    indice = IndiceVetorial(config, base)
    desatualizados = indice.desatualizados(ingestion.ler_manifesto(config))
    if desatualizados:
        print(f"Índice desatualizado para {desatualizados}; indexe o acervo antes da rodada.")
        return 1
    catalogo = json.loads((config.caminho("originais") / "desafio-2" / "casos.json").read_text(encoding="utf-8"))

    def cliente():
        return base.nova_execucao(guardrails.ControleRecursos(config))

    for parte in args.partes:
        funcao, nome = PARTES[parte]
        saida = {"executado_em": agora_iso(), "perfil": config.perfil_geracao()["nome"],
                 "modelo": config.perfil_geracao()["modelo"],
                 "indice": {k: indice.info()[k] for k in ("chunking", "versao_indice")},
                 **funcao(config, auditoria, indice, cliente, catalogo)}
        linhas = [linha for valor in saida.values() if isinstance(valor, list) for linha in valor]
        saida["custo_estimado_usd"] = round(sum(l["custo_estimado_usd"] for l in linhas), 6)
        caminho = config.caminho("metricas") / nome
        caminho.write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{parte}: custo estimado US$ {saida['custo_estimado_usd']}; saída em {config.relativo(caminho)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
