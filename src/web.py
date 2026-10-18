"""Interface local (python -m src.main interface): API sobre as mesmas funções da CLI e o front-end compilado.

Escuta só em 127.0.0.1. As decisões continuam humanas: a interface repassa o
que o operador escolheu para fluxo.py e revisao.py, que registram no mesmo log da CLI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import avaliacao, fluxo
from .audit import Auditoria
from .config import CasoInexistente, Config
from .entradas import ArquivoInvalido
from .image_generation import ErroPeca
from .llm_client import ClienteLLM, ErroLLM
from .revisao import (
    AGUARDANDO,
    CAMPOS_CRITICOS,
    CHECKLIST_PECA,
    DECISOES,
    RevisaoInvalida,
    ler_metadados,
    registrar_decisao,
    registrar_revisao_peca,
    resumo_revisoes,
)
from .tipos import PendenteDeImplementacao

# /api/arquivo só serve o que está nestas pastas: nunca .env, código ou prompts de sistema.
PASTAS_LIBERADAS = ("dados", "resultados")
DIST = Path(__file__).resolve().parent.parent / "interface" / "dist"
ESPECIFICACAO_PECA = "prompts/peca_visual_v1.json"


class Confirmacao(BaseModel):
    campos: dict[str, str]
    revisor: str


class Decisao(BaseModel):
    decisao: str
    justificativa: str
    revisor: str
    texto_corrigido: str | None = None


class DecisaoPeca(BaseModel):
    checklist: dict[str, bool]
    decisao: str
    justificativa: str
    revisor: str


class PedidoPeca(BaseModel):
    caso_id: str


def criar_app(config: Config, *, fabrica_cliente: Callable[[], ClienteLLM] | None = None) -> FastAPI:
    app = FastAPI(title="Central de Atendimento — Desafio 1")
    novo_cliente = fabrica_cliente or (lambda: ClienteLLM(config))

    def erro(status: int):
        async def tratar(_: Request, excecao: Exception) -> JSONResponse:
            return JSONResponse({"erro": str(excecao)}, status_code=status)

        return tratar

    app.add_exception_handler(ErroLLM, erro(502))
    app.add_exception_handler(PendenteDeImplementacao, erro(501))
    for classe in (ArquivoInvalido, CasoInexistente, ErroPeca, RevisaoInvalida):
        app.add_exception_handler(classe, erro(400))

    def ler_jsons(pasta: Path) -> list[dict]:
        return [json.loads(c.read_text(encoding="utf-8")) for c in sorted(pasta.glob("*.json"))]

    @app.get("/api/painel")
    def painel() -> dict:
        avaliacoes = {a["id_execucao"]: a for a in avaliacao.avaliar_todas(config)}
        minutas = [
            {**m, "falhas": avaliacoes.get(m["id_execucao"], {}).get("falhas")}
            for m in ler_jsons(config.caminho("minutas"))
        ]
        pendentes = [
            {k: e[k] for k in ("id_execucao", "caso_id", "modalidade", "preparado_em")}
            for e in fluxo.pendentes_de_confirmacao(config)
        ]
        return {
            "casos": config.dados["casos"],
            "pendentes": pendentes,
            "minutas": sorted(minutas, key=lambda m: m["gerada_em"], reverse=True),
            "pecas": sorted(ler_jsons(config.caminho("imagens")), key=lambda p: p["data_geracao"], reverse=True),
            "resumo": resumo_revisoes(config),
            "checklist_peca": CHECKLIST_PECA,
        }

    @app.post("/api/casos/{caso_id}/processar")
    def processar(caso_id: str) -> dict:
        config.caso(caso_id)
        cliente, auditoria = novo_cliente(), Auditoria(config)
        estado = fluxo.preparar_caso(caso_id, config=config, cliente=cliente, auditoria=auditoria)
        if estado["exige_confirmacao"]:
            return {"confirmacao": estado["id_execucao"]}
        metadados = fluxo.concluir_caso(
            estado["id_execucao"], campos_confirmados=None, config=config, cliente=cliente, auditoria=auditoria
        )
        return {"minuta": metadados["id_execucao"]}

    @app.get("/api/execucoes/{id_execucao}")
    def execucao(id_execucao: str) -> dict:
        estado, pasta = fluxo.ler_estado(config, id_execucao)
        textos = {
            nome: (pasta / f"{nome}.txt").read_text(encoding="utf-8")
            for nome in ("texto_bruto", "texto_revisado")
            if (pasta / f"{nome}.txt").is_file()
        }
        # Sem gabarito nem comparação: a confirmação tem que ser feita olhando o original.
        return {**estado, **textos, "campos_criticos": list(CAMPOS_CRITICOS)}

    @app.post("/api/execucoes/{id_execucao}/confirmar")
    def confirmar(id_execucao: str, corpo: Confirmacao) -> dict:
        if not corpo.revisor.strip():
            raise RevisaoInvalida("Informe quem conferiu os dados.")
        metadados = fluxo.concluir_caso(
            id_execucao,
            campos_confirmados=corpo.campos,
            revisor=corpo.revisor.strip(),
            config=config,
            cliente=novo_cliente(),
            auditoria=Auditoria(config),
        )
        return {"minuta": metadados["id_execucao"]}

    @app.get("/api/minutas/{id_execucao}")
    def minuta(id_execucao: str) -> dict:
        metadados = ler_metadados(config, id_execucao)
        extracao = json.loads((config.raiz / metadados["extracao"]).read_text(encoding="utf-8"))
        return {
            **metadados,
            "texto": (config.raiz / metadados["arquivo_minuta"]).read_text(encoding="utf-8"),
            "campos": extracao["campos"],
            "campos_corrigidos_por_humano": extracao.get("campos_corrigidos_por_humano", []),
            "avaliacao": avaliacao.avaliar_minuta(metadados, config),
            "decisoes": list(DECISOES),
        }

    @app.post("/api/minutas/{id_execucao}/decisao")
    def decidir_minuta(id_execucao: str, corpo: Decisao) -> dict:
        metadados = ler_metadados(config, id_execucao)
        # Checado antes de gravar a correção: minuta revisada não pode mudar de texto.
        if metadados["status"] != AGUARDANDO:
            raise RevisaoInvalida(f"Esta minuta já foi revisada (status: {metadados['status']}).")
        if corpo.decisao not in DECISOES or not corpo.justificativa.strip() or not corpo.revisor.strip():
            raise RevisaoInvalida("Escolha uma decisão válida e informe justificativa e revisor.")
        if corpo.decisao == "aprovar_com_correcao":
            if not (corpo.texto_corrigido or "").strip():
                raise RevisaoInvalida("Aprovar com correção exige o texto corrigido.")
            (config.raiz / metadados["arquivo_minuta"]).write_text(corpo.texto_corrigido.strip() + "\n", encoding="utf-8")
        elif corpo.texto_corrigido is not None:
            raise RevisaoInvalida("Texto corrigido só é aceito com a decisão aprovar_com_correcao.")
        return registrar_decisao(
            config, Auditoria(config), id_execucao,
            decisao=corpo.decisao, justificativa=corpo.justificativa, revisor=corpo.revisor,
        )

    @app.post("/api/minutas/{id_execucao}/audio")
    def audio_minuta(id_execucao: str) -> dict:
        return fluxo.sintetizar_minuta(id_execucao, config=config, cliente=novo_cliente(), auditoria=Auditoria(config))

    @app.post("/api/pecas")
    def gerar_peca(corpo: PedidoPeca) -> dict:
        especificacao = json.loads((config.raiz / ESPECIFICACAO_PECA).read_text(encoding="utf-8"))
        peca = fluxo.gerar_peca_visual(
            corpo.caso_id, especificacao, imagem_base=None, config=config, cliente=novo_cliente(), auditoria=Auditoria(config)
        )
        return {"peca": peca.caminho.stem}

    @app.get("/api/pecas/{id_execucao}")
    def peca(id_execucao: str) -> dict:
        caminho = config.caminho("imagens") / f"{id_execucao}.json"
        if not caminho.is_file():
            raise RevisaoInvalida(f"Nenhuma peça visual com id de execução {id_execucao}.")
        return {**json.loads(caminho.read_text(encoding="utf-8")), "checklist_peca": CHECKLIST_PECA}

    @app.post("/api/pecas/{id_execucao}/decisao")
    def decidir_peca(id_execucao: str, corpo: DecisaoPeca) -> dict:
        return registrar_revisao_peca(
            config, Auditoria(config), id_execucao,
            checklist=corpo.checklist, decisao=corpo.decisao, justificativa=corpo.justificativa, revisor=corpo.revisor,
        )

    @app.get("/api/arquivo")
    def arquivo(caminho: str) -> FileResponse:
        alvo = (config.raiz / caminho).resolve()
        liberado = any(alvo.is_relative_to((config.raiz / pasta).resolve()) for pasta in PASTAS_LIBERADAS)
        if not liberado or not alvo.is_file():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
        return FileResponse(alvo)

    if DIST.is_dir():
        app.mount("/", StaticFiles(directory=DIST, html=True), name="interface")
    else:

        @app.get("/")
        def sem_interface() -> dict:
            return {"erro": "Interface não compilada: rode `npm install && npm run build` em interface/."}

    return app
