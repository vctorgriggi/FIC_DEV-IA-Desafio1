"""Registro e rastreabilidade (RF11).

Cada evento vira uma linha JSON em resultados/logs/execucoes.jsonl. O log guarda
referências (caminhos, versão e hash do prompt), não o conteúdo: a saída se
reconstrói a partir do arquivo de origem, do prompt versionado e dos parâmetros.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from .config import Config, carregar_chave
from .llm_client import RespostaLLM
from .privacidade import ocultar_segredos


def novo_id() -> str:
    return uuid.uuid4().hex[:12]


def agora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class Evento:
    id_execucao: str
    caso_id: str
    etapa: str
    modalidade: str | None = None
    arquivo_origem: str | None = None
    provedor: str | None = None
    modelo: str | None = None
    parametros: dict | None = None
    versao_prompt: str | None = None
    hash_prompt: str | None = None
    saida: str | None = None
    duracao_s: float | None = None
    tokens_entrada: int | None = None
    tokens_saida: int | None = None
    custo_estimado_usd: float | None = None
    erro: str | None = None
    decisao_humana: str | None = None
    justificativa: str | None = None
    revisor: str | None = None
    extra: dict[str, Any] | None = None

    def com_resposta(self, resposta: RespostaLLM) -> Evento:
        self.modelo = resposta.modelo
        self.parametros = resposta.parametros
        self.duracao_s = resposta.duracao_s
        self.tokens_entrada = resposta.tokens_entrada
        self.tokens_saida = resposta.tokens_saida
        self.custo_estimado_usd = resposta.custo_estimado_usd
        return self


class Auditoria:
    def __init__(self, config: Config, *, segredos: list[str] | None = None):
        self.config = config
        self.arquivo = config.caminho("logs") / "execucoes.jsonl"
        self._segredos = segredos if segredos is not None else [carregar_chave() or ""]

    def registrar(self, evento: Evento) -> dict:
        registro = {"id_evento": novo_id(), "data_hora": agora_iso(), **asdict(evento)}
        if registro["provedor"] is None and registro["modelo"] is not None:
            registro["provedor"] = self.config.dados["provedor"]
        linha = ocultar_segredos(json.dumps(registro, ensure_ascii=False, default=str), self._segredos)
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        with open(self.arquivo, "a", encoding="utf-8") as arquivo:
            arquivo.write(linha + "\n")
        return json.loads(linha)

    def eventos(self, **filtro: Any) -> list[dict]:
        if not self.arquivo.exists():
            return []
        with open(self.arquivo, encoding="utf-8") as arquivo:
            registros = [json.loads(linha) for linha in arquivo if linha.strip()]
        return [r for r in registros if all(r.get(k) == v for k, v in filtro.items())]
