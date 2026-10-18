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
# RF10: o que conferir na peça visual antes de aprová-la.
CHECKLIST_PECA = {
    "textos": "Textos corretos, completos e legíveis?",
    "simbolos_objetos": "Símbolos e objetos coerentes, sem deformação?",
    "pessoas_maos": "Sem pessoa real e sem rosto ou mão deformados?",
    "coerencia": "Coerente com o caso e com a orientação?",
    "proveniencia": "Selo de conteúdo gerado por IA visível?",
}
ATALHOS_PECA = {"a": "aprovar", "r": "rejeitar", "n": "nova_geracao"}


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


def perguntar_decisao(
    perguntar: Callable[[str], str] | None = None, atalhos: dict[str, str] = ATALHOS
) -> tuple[str, str, str]:
    perguntar = perguntar or input
    opcoes = "  ".join(f"[{atalho}] {nome}" for atalho, nome in atalhos.items())
    while (decisao := atalhos.get(perguntar(f"Decisão — {opcoes}: ").strip().lower())) is None:
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


def perguntar_checklist_peca(perguntar: Callable[[str], str] | None = None) -> dict[str, bool]:
    perguntar = perguntar or input
    respostas = {}
    for chave, pergunta in CHECKLIST_PECA.items():
        while (resposta := perguntar(f"  {pergunta} [s/n] ").strip().lower()) not in ("s", "n"):
            pass
        respostas[chave] = resposta == "s"
    return respostas


def registrar_revisao_peca(
    config: Config,
    auditoria: Auditoria,
    id_execucao: str,
    *,
    checklist: dict[str, bool],
    decisao: str,
    justificativa: str,
    revisor: str,
) -> dict:
    """RF10: a peça só é aprovada com todos os itens do checklist conferidos."""
    if set(checklist) != set(CHECKLIST_PECA):
        raise RevisaoInvalida(f"O checklist precisa ter exatamente: {', '.join(CHECKLIST_PECA)}.")
    if decisao not in ATALHOS_PECA.values():
        raise RevisaoInvalida(f"Decisão desconhecida: {decisao}. Opções: {', '.join(ATALHOS_PECA.values())}.")
    if decisao == "aprovar" and not all(checklist.values()):
        reprovados = ", ".join(c for c, ok in checklist.items() if not ok)
        raise RevisaoInvalida(f"Peça com item reprovado ({reprovados}) não pode ser aprovada; rejeite ou peça nova geração.")
    if not justificativa.strip():
        raise RevisaoInvalida("A justificativa é obrigatória.")
    if not revisor.strip():
        raise RevisaoInvalida("Informe quem revisou.")

    caminho = config.caminho("imagens") / f"{id_execucao}.json"
    if not caminho.exists():
        raise RevisaoInvalida(f"Nenhuma peça visual com id de execução {id_execucao}.")
    metadados = json.loads(caminho.read_text(encoding="utf-8"))
    if metadados["status"] != AGUARDANDO:
        raise RevisaoInvalida(f"Esta peça já foi revisada (status: {metadados['status']}).")

    metadados["status"] = DECISOES[decisao]
    metadados["revisao"] = {
        "checklist": checklist,
        "decisao": decisao,
        "justificativa": justificativa.strip(),
        "revisor": revisor.strip(),
        "data_hora": agora_iso(),
        "sha256_peca": hash_arquivo(config.raiz / metadados["imagem"]),
    }
    caminho.write_text(json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8")
    auditoria.registrar(
        Evento(
            id_execucao=id_execucao,
            caso_id=metadados["caso_id"],
            etapa="revisao_peca",
            saida=metadados["imagem"],
            decisao_humana=decisao,
            justificativa=justificativa.strip(),
            revisor=revisor.strip(),
            extra={"checklist": checklist},
        )
    )
    return metadados
