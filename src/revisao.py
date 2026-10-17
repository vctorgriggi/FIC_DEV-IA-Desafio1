"""Revisão humana (RF13; seção 8, etapa Revisão).

Não existe envio ao cidadão em lugar nenhum do código: o ponto final de uma
minuta é a decisão registrada de um servidor.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

from .audit import Auditoria, Evento, agora_iso
from .config import Config

AGUARDANDO = "aguardando_revisao"
DECISOES = {
    "aprovar": "aprovada",
    "aprovar_com_correcao": "aprovada_com_correcao",
    "rejeitar": "rejeitada",
    "nova_geracao": "nova_geracao_solicitada",
}
ATALHOS = {"a": "aprovar", "c": "aprovar_com_correcao", "r": "rejeitar", "n": "nova_geracao"}
STATUS_APROVADOS = ("aprovada", "aprovada_com_correcao")
# RF06 e RF08: conferidos por uma pessoa antes da minuta quando vêm de áudio ou imagem.
CAMPOS_CRITICOS = ("protocolo", "data", "solicitante")


class RevisaoInvalida(ValueError):
    pass


def caminho_metadados(config: Config, id_execucao: str) -> Path:
    return config.caminho("minutas") / f"{id_execucao}.json"


def ler_metadados(config: Config, id_execucao: str) -> dict:
    caminho = caminho_metadados(config, id_execucao)
    if not caminho.exists():
        raise RevisaoInvalida(f"Nenhuma minuta com id de execução {id_execucao}.")
    return json.loads(caminho.read_text(encoding="utf-8"))


def gravar_metadados(config: Config, metadados: dict) -> None:
    caminho = caminho_metadados(config, metadados["id_execucao"])
    caminho.write_text(json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8")


def hash_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def registrar_decisao(
    config: Config,
    auditoria: Auditoria,
    id_execucao: str,
    *,
    decisao: str,
    justificativa: str,
    revisor: str,
) -> dict:
    if decisao not in DECISOES:
        raise RevisaoInvalida(f"Decisão desconhecida: {decisao}. Opções: {', '.join(DECISOES)}.")
    if not justificativa.strip():
        raise RevisaoInvalida("A justificativa é obrigatória.")
    if not revisor.strip():
        raise RevisaoInvalida("Informe quem revisou.")

    metadados = ler_metadados(config, id_execucao)
    if metadados["status"] != AGUARDANDO:
        raise RevisaoInvalida(f"Esta minuta já foi revisada (status: {metadados['status']}).")

    arquivo_minuta = config.raiz / metadados["arquivo_minuta"]
    metadados["status"] = DECISOES[decisao]
    metadados["revisao"] = {
        "decisao": decisao,
        "justificativa": justificativa.strip(),
        "revisor": revisor.strip(),
        "data_hora": agora_iso(),
        # RF07: o áudio só sai do texto exatamente como foi aprovado.
        "sha256_minuta": hash_arquivo(arquivo_minuta),
    }
    gravar_metadados(config, metadados)
    auditoria.registrar(
        Evento(
            id_execucao=id_execucao,
            caso_id=metadados["caso_id"],
            etapa="revisao",
            modalidade=metadados["modalidade"],
            arquivo_origem=metadados["arquivo_origem"],
            saida=metadados["arquivo_minuta"],
            decisao_humana=decisao,
            justificativa=justificativa.strip(),
            revisor=revisor.strip(),
        )
    )
    return metadados


def resumo_revisoes(config: Config) -> dict:
    """RF13: contagem por status e taxas de aprovação sobre as minutas já revisadas."""
    por_status: dict[str, int] = {}
    for caminho in sorted(config.caminho("minutas").glob("*.json")):
        status = json.loads(caminho.read_text(encoding="utf-8"))["status"]
        por_status[status] = por_status.get(status, 0) + 1
    revisadas = sum(n for status, n in por_status.items() if status != AGUARDANDO)
    aprovadas = por_status.get("aprovada", 0)
    corrigidas = por_status.get("aprovada_com_correcao", 0)
    return {
        "por_status": por_status,
        "revisadas": revisadas,
        "taxa_aprovacao_sem_correcao": round(aprovadas / revisadas, 3) if revisadas else None,
        "taxa_aprovacao_com_correcao": round((aprovadas + corrigidas) / revisadas, 3) if revisadas else None,
    }


def perguntar_decisao(perguntar: Callable[[str], str] | None = None) -> tuple[str, str, str]:
    perguntar = perguntar or input
    opcoes = "  ".join(f"[{atalho}] {nome}" for atalho, nome in ATALHOS.items())
    while (decisao := ATALHOS.get(perguntar(f"Decisão — {opcoes}: ").strip().lower())) is None:
        pass
    while not (justificativa := perguntar("Justificativa: ").strip()):
        pass
    while not (revisor := perguntar("Revisor (nome ou função fictícia): ").strip()):
        pass
    return decisao, justificativa, revisor


def confirmar_campos_criticos(
    campos: dict,
    perguntar: Callable[[str], str] | None = None,
    mostrar: Callable[[str], None] | None = None,
) -> tuple[dict, list[str]]:
    """Mostra cada campo crítico; Enter confirma, qualquer texto substitui o valor."""
    perguntar = perguntar or input
    mostrar = mostrar or print
    mostrar("Confira os dados críticos extraídos (Enter confirma, ou digite o valor correto):")
    confirmados = dict(campos)
    corrigidos = []
    for campo in CAMPOS_CRITICOS:
        resposta = perguntar(f"  {campo} = {campos.get(campo)!r} > ").strip()
        if resposta:
            confirmados[campo] = resposta
            corrigidos.append(campo)
    return confirmados, corrigidos
